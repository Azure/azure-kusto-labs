# About

This module covers the following steps that essentially sets the stage for integration.  It is an involved module, a step missed may mean, things dont work for you.  Grab a acup of coffee/tea and get started.  It should take an hour or two.

1.  Create a Docker Hub account if it does not exist
2.  Install Docker desktop on your machine
3.  Build a docker image for the KafkaConnect worker that include any connect worker level configurations, and the ADX connector jar
4.  Push the image to the Docker hub
5.  Provision KafkaConnect workers on our Azure Kubernetes Service cluster
6.  Install Postman on our local machine
7.  Import KafkaConnect REST call JSON collection from Github into Postman
8.  Launch the Kafka-ADX copy tasks, otherwise called connector tasks

## 1.  Create a Docker Hub account

Follow the instructions [here](https://hub.docker.com/signup) and create an account.  Note down your user ID and password.

## 2.  Install Docker desktop on your machine and launch it

Follow the instructions [here](https://www.docker.com/products/docker-desktop) and complete the installation and start the service.

## 3. Build a Docker image

### 3.1. Create a local directory

In linux/Mac-
```
cd ~
mkdir kafka-confluentcloud-hol
cd kafka-confluentcloud-hol
```

### 3.2. Download the ADX connector jar

Run the following commands-
<br>
1.  Switch directories if needed
```
cd ~/kafka-confluentcloud-hol
```
2.  Download the jar
```
wget https://github.com/Azure/kafka-sink-azure-kusto/releases/download/v1.0.1/kafka-sink-azure-kusto-1.0.1-jar-with-dependencies.jar 
```

### 3.3. Create a Docker file

Start a file-
```
vi connect-worker-image-builder.dockerfile
```

Paste this into the file and save - be sure to edit it for bootstrap server list, Kafka API key and Kafka API secrte to reflect yours..
```
FROM confluentinc/cp-kafka-connect:5.5.0
COPY kafka-sink-azure-kusto-1.0.1-jar-with-dependencies.jar /usr/share/java

ENV CONNECT_CONNECTOR_CLIENT_CONFIG_OVERRIDE_POLICY="All"

ENV producer.bootstrap.servers="YOUR-BOOTSTRAP-SERVER-LIST"
ENV producer.security.protocol="SASL_SSL"
ENV producer.ssl.endpoint.identification.algorithm="https"
ENV producer.sasl.mechanism="PLAIN"
ENV producer.sasl.jaas.config="org.apache.kafka.common.security.plain.PlainLoginModule required username=\"YOUR-KAFKA-API-KEY\" password=\YOUR-KAFKA-API-SECRET"\";"

```

What we are doing above is taking the base Docker image from the ConfluentInc repo, copying the ADX jar to /usr/share/java and setting an environment variable to allow overrides at the consumer level.

### 3.4. Create a Docker image off of 3.3

Replace akhanolkar with your docker UID and run the below-
```
sudo docker build -t akhanolkar/kafka-connect-kusto-sink:1.0.1v1 -f connect-worker-image-builder.dockerfile .
```

List the images created-
```
docker image list
```

Author's output:
```
indra:kafka-confluentcloud-hol akhanolk$ docker image list
REPOSITORY                                    TAG                 IMAGE ID            CREATED             SIZE
akhanolkar/kafka-connect-kusto-sink           1.0.1v1             1870ace80b29        23 seconds ago      1.24GB
```

## 4. Push the image to Docker Hub
Run the command below, replacing akhanolkar with your Docker username-
```
docker push akhanolkar/kafka-connect-kusto-sink:1.0.1v1
```

Author's output-
```
indra:kafka-confluentcloud-hol akhanolk$ docker push akhanolkar/kafka-connect-kusto-sink:1.0.1v1
The push refers to repository [docker.io/akhanolkar/kafka-connect-kusto-sink]
958960eb74db: Pushed 
c20428756bff: Layer already exists 
75cd0f16c778: Layer already exists 
b1aa21789e59: Layer already exists 
0d9a93e8c391: Layer already exists 
05c69d782ee2: Layer already exists 
fb73194a06ee: Layer already exists 
bc537b2bbfd6: Layer already exists 
0818dd46b53a: Layer already exists 
19e377f490b1: Layer already exists 
a8ff4211732a: Layer already exists 
1.0.1v1: digest: sha256:ae32c964bf277298b1541f52d956c6e6a5dc1263262178f8a9950e3244eacd71 size: 2639
```

You should be able to see the image in Docker Hub.

## 5. Clone KafkaConnect helm charts from Confluent git repo & make necessary edits

### 5.1. Clone the repo and copy what is required
```
cd ~
git clone https://github.com/confluentinc/cp-helm-charts.git

cd ~/kafka-confluentcloud-hol
cp -R ~/cp-helm-charts/charts/cp-kafka-connect .
```

### 5.2. A quick browse

```
indra:kafka-confluentcloud-hol akhanolk$ tree cp-kafka-connect/
cp-kafka-connect/
├── Chart.yaml
├── README.md
├── templates
│   ├── NOTES.txt
│   ├── _helpers.tpl
│   ├── deployment.yaml
│   ├── jmx-configmap.yaml
│   ├── secrets.yaml
│   └── service.yaml
└── values.yaml
```

Note the values.yaml - we will need to update this.

### 5.3. Update values.yaml as follows

We need to update the values.yaml with the following-<br>
1. Replica count
```
replicaCount: 6
```

2. Image<br>
Your docker ID, inplace of akhanolkar
```
image: akhanolkar/kafka-connect-kusto-sink
imageTag: 1.0.1v1
```
3. Kafka bootstrap servers<br>
Replace "yourBootStrapServerList" with your Confluent Cloud bootstrap server loadbalancer FQDN:Port
```
kafka:
  bootstrapServers: "yourBootStrapServerList"
 ```


## 6. Provision KafkaConnect workers on our Azure Kubernetes Service cluster

### 6.1. Login to Azure CLI & set the subscription to use
[Install if it does not exist.](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)<br>

1. Login
```
az login
```
This will launch the Azure portal, sign-in dialog.  Sign-in.<br>

2. Switch to the right Azure subscription in case you have multiple
```
az account set --subscription YOUR_SUBSCRIPTION_GUID
```
