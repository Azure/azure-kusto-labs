##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with Confluent Platform](README.md)
<hr>

# 1. FOCUS: CREATE CONNECTOR DOCKER IMAGE
This module covers creation of a Docker image of the Confluent bits + ADX Kafka connector plugin, and publishing to Docker hub.  It then covers updating the Azure YAML to leverage your image for the cluster.

# 2. Process overview
1) We need to take the base docker image of the Confluent Operator for KafkaConnect and overlay to include the Kusto connector in the /usr/share/java directory.<br>
2) Location of the base helm chart for this needs studying, and its located here..<br>
opt/kafka/confluent-operator/helm/confluent-operator/charts/connect/values.yaml
```
image:
  repository: confluentinc/cp-server-connect-operator
  tag: 5.5.0.0
```
3) We will grab the coordinates and create out own docker image and publish it to docker hub<br>
4) Then we will leverage our global provider file (opt/kafka/confluent-operator/helm/providers/zeus-azure.yaml) to override the base image setting with our coordinates from #3<br>
5) When we install Connect, the pods will  have our connector jar in /usr/share/java<br>

# 3. Build and publish docker image

### 3.1. Create Dockerfile

1) Download the Kusto jar locally...in my case..
The Kusto jar is located here..
https://github.com/Azure/kafka-sink-azure-kusto/releases/
<br>
Select the latest release version and download locally
```
cd opt/kafka/docker-image-build/
wget https://github.com/Azure/kafka-sink-azure-kusto/releases/download/0.3.4/kafka-sink-azure-kusto-0.3.4-jar-with-dependencies.jar
```
In the author's case..
```
opt/kafka/docker-image-build/kafka-sink-azure-kusto-0.3.4-jar-with-dependencies.jar
```

2) Create Dockerfile
```
cd opt/kafka/docker-image-build
vi confluent-connector-image-builder.dockerfile 
```

3) Paste into Dockerfile..
```
FROM confluentinc/cp-server-connect-operator:5.5.0.0
COPY kafka-sink-azure-kusto-0.3.4-jar-with-dependencies.jar /usr/share/java
```


### 3.2. Build image

```
sudo docker build -t akhanolkar/cp-server-connect-operator-kusto:0.3.4v1 -f confluent-connector-image-builder.dockerfile  .
```

Output...
```
Sending build context to Docker daemon  60.12MB
Step 1/2 : FROM confluentinc/cp-server-connect-operator:5.5.0.0
5.5.0.0: Pulling from confluentinc/cp-server-connect-operator
3707da5d6610: Already exists 
dba8c1d87339: Already exists 
d3d8e9b13a8a: Already exists 
94b37b8de5ff: Already exists 
e79c28c9796e: Pull complete 
c25995434721: Pull complete 
7c80143b9821: Pull complete 
4ae677cf9a6a: Pull complete 
fa1e0edb9f48: Pull complete 
13d7981c86e1: Pull complete 
c19da367b86c: Pull complete 
36125c3f0bfb: Pull complete 
05850f442b7a: Pull complete 
ea5b2745dee8: Pull complete 
41e51fe25c7b: Pull complete 
Digest: sha256:37c42cf5d835c6b0c5d826b71c383b433b678b581b18c93db9aeee2c04052ecf
Status: Downloaded newer image for confluentinc/cp-server-connect-operator:5.5.0.0
 ---> e09da787ba34
Step 2/2 : COPY kafka-sink-azure-kusto-0.3.4-jar-with-dependencies.jar /usr/share/java
 ---> 9031cc34d01d
Successfully built 9031cc34d01d
Successfully tagged akhanolkar/cp-server-connect-operator-kusto:0.3.4v1
```

Validate in local docker repo...
```
REPOSITORY                                    TAG                 IMAGE ID            CREATED             SIZE
akhanolkar/cp-server-connect-operator-kusto   0.3.4v1             9031cc34d01d        8 minutes ago       1.53GB
```

### 3.3. Publish image to dockerhub

```
docker push akhanolkar/cp-server-connect-operator-kusto:0.3.4v1
```


### 3.4. Update global cloud provider YAML

Update the global provider file to have the following as the section for Connect..<br>
Replace ```akhanolkar/cp-server-connect-operator-kusto``` with your docker repo.


```
## Connect Cluster
##
connect:
  name: connectors
  replicas: 6
  image:
    repository: akhanolkar/cp-server-connect-operator-kusto
    tag: 0.3.4v1
  tls:
    enabled: false
    ## "" for none, "tls" for mutual auth
    authentication:
      type: ""
    fullchain: |-
    privkey: |-
    cacerts: |-
  loadBalancer:
    enabled: false
    domain: ""
  dependencies:
    kafka:
      bootstrapEndpoint: kafka:9071
      brokerCount: 3
    schemaRegistry:
      enabled: true
      url: http://schemaregistry:8081
```

