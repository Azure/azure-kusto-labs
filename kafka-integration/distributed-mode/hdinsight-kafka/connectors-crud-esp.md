# About this module
This module covers the following steps that essentially set the stage for integration - specific to HDInsight Kafka with Enterprise Service Package (Kerberos enabled).

![CONNECTOR](images/connector-CRUD.png)
<br>
<br>
<hr>
<br>

[1. Create a local directory](connectors-crud-esp.md#1-create-a-local-directory)<br>
[2. Download configs you need from HDInsight ESP Kafka cluster](connectors-crud-esp.md#2--download-configs-you-need-from-hdinsight-esp-kafka-cluster)<br>
[3. Create a Docker Hub account](connectors-crud-esp.md#3--create-a-docker-hub-account)<br>
[4. Install Docker desktop on your machine and launch it](connectors-crud-esp.md#4--install-docker-desktop-on-your-machine-and-launch-it)<br>
[5. Build a Docker image of the Kafka Connect worker](connectors-crud-esp.md#5-build-a-docker-image-of-the-kafka-connect-worker)<br>
[6. Push the image to Docker Hub](connectors-crud-esp.md#6-push-the-image-to-docker-hub)<br>
[7. Clone KafkaConnect helm charts from Confluent git repo & make necessary edits](connectors-crud-esp.md#7-clone-kafkaconnect-helm-charts-from-confluent-git-repo--make-necessary-edits)<br>
[8. Provision KafkaConnect workers on our Azure Kubernetes Service cluster](connectors-crud-esp.md#8-provision-kafkaconnect-workers-on-our-azure-kubernetes-service-cluster)<br>
[9. Start port forwarding to be able to make REST calls from your machine to KafkaConnect service running on AKS pods](connectors-crud-esp.md#9-start-port-forwarding-to-be-able-to-make-rest-calls-from-your-machine-to-kafkaconnect-service-running-on-aks-pods)<br>
[10. Download & install Postman](connectors-crud-esp.md#10-download--install-postman)<br>
[11. Import the Postman JSON collection with KafkaConnect REST API call samples](connectors-crud-esp.md#11-import-the-postman-json-collection-with-kafkaconnect-rest-api-call-samples)<br>
[12. Validate data delivery in Azure Data Explorer](connectors-crud-esp.md#12-validate-data-delivery-in-azure-data-explorer)<br>


The following section strives to explain further, pictorially, what we are doing in the lab, for clarity.<br>

## Part A

1.  Create a Docker Hub account if it does not exist
2.  Install Docker desktop on your machine
3.  Build a docker image for the KafkaConnect worker that include any connect worker level configurations, and the ADX connector jar
4.  Push the image to the Docker hub
<br>

![CONNECTOR](images/AKS-Image-Creation.png)
<br>
<br>
<hr>
<br>

## Part B

5.  Provision KafkaConnect workers on our Azure Kubernetes Service cluster

When we start off, all we have is an empty Kubernetes cluster-

![CONNECTOR](images/AKS-Empty.png)
<br>
<br>
<hr>
<br>

When we are done, we have a live KafkaConnect cluster that is integrated with the Kafka cluster (HDI ESP in this case)-

![CONNECTOR](images/AKS-KafkaConnect.png)
<br>
<br>
<hr>
<br>

Note: This still does not have copy tasks (connector tasks) running yet

## Part C

6.  Install Postman on our local machine
7.  Import KafkaConnect REST call JSON collection from Github into Postman

## Part D

8.  Launch the Kafka-ADX copy tasks, otherwise called connector tasks

This is what we have at the end of this module, a Kusto sink connector cluster with copy tasks running.

![CONNECTOR](images/AKS-Connector-Cluster.png)
<br>
<br>
<hr>
<br>

![CONNECTOR](images/AKS-ADX.png)
<br>
<br>
<hr>
<br>

## 1. Create a local directory

In linux/Mac-
```
cd ~
mkdir kafka-hdi-hol
cd kafka-hdi-hol
```

## 2.  Download configs you need from HDInsight ESP Kafka cluster

From the connector AKS cluster, we have to consume from kerberized HDInsight Kafka. For this, we need a user principal that has Ranger policy set to consume from Kafka, and also to create topics (Kafka Connect creates 3 topics per deployment of Kafka Connect cluster).  In this example, we wil use the user **hdiadminjrs**.

### 2.1.  Ranger policy for UPN to be used in the lab

![RANGER](images/ranger-01.png)
<br>
<br>
<hr>
<br>

![RANGER](images/ranger-02.png)
<br>
<br>
<hr>
<br>

![RANGER](images/ranger-03.png)
<br>
<br>
<hr>
<br>

### 2.2. Generate Kerberos keytab for UPN with Kafka topic create/write access configured in Ranger

Connect to the head node of the HDInsight cluster and generate a headless keytab for the privileged user-
```
ktutil
addent -password -p <UPN>@<REALM> -k 1 -e RC4-HMAC
wkt <UPN>-headless.keytab
```

E.g. hdiadminjrs is the cluster administrator.  The realm is AADDS.JRSMYDOMAIN.COM.  The keytab name is kafka-client-hdi.keytab.
```
ktutil
addent -password -p hdiadminjrs@AADDS.JRSMYDOMAIN.COM -k 1 -e RC4-HMAC
wkt kafka-client-hdi.keytab
```

Copy the keytab from HDInsight to your local directory.  Example...
```
# From your local machine..
cd  kafka-hdi-hol

scp sshuser@democluster-ssh.azurehdinsight.net:/home/AADDS/hdiadminjrs/kafka-client-hdi.keytab .
```

### 2.3. krb5.conf from the HDI cluster download the krb5.conf

```
# From your local machine..
cd  kafka-hdi-hol

scp sshuser@democluster-ssh.azurehdinsight.net:/etc/krb5.conf .

```

### 2.4. Create a HDI JaaS conf

Create a JaaS confiog file as follows-

```
cd ~/kafka-hdi-hol
vi hdi-esp-jaas.conf
```

Paste this into the file, after updating with your UPN (hdiadminjrs) and Kerberos realm (AADDS.JRSMYDOMAIN.COM)-
```
KafkaClient {
    com.sun.security.auth.module.Krb5LoginModule required
    useKeyTab=true
    storeKey=true
    keyTab="/etc/security/keytabs/kafka-client-hdi.keytab"
    principal="hdiadminjrs@AADDS.JRSMYDOMAIN.COM";
};
```

## 3.  Create a Docker Hub account

Follow the instructions [here](https://hub.docker.com/signup) and create an account.  Note down your user ID and password.

## 4.  Install Docker desktop on your machine and launch it

Follow the instructions [here](https://www.docker.com/products/docker-desktop) and complete the installation and start the service.

## 5. Build a Docker image of the Kafka Connect worker

### 5.1. Download the ADX connector jar

Run the following commands-
<br>
1.  Switch directories if needed
```
cd ~/kafka-hdi-hol
```
2.  Download the jar
```
wget https://github.com/Azure/kafka-sink-azure-kusto/releases/download/v1.0.1/kafka-sink-azure-kusto-1.0.1-jar-with-dependencies.jar 
```

### 5.2. Review directory contents so far

You should already have this.
```
cd ~/kafka-hdi-hol
tree

├── hdi-esp-jaas.conf
├── kafka-client-hdi.keytab
├── kafka-sink-azure-kusto-1.0.1-jar-with-dependencies.jar
└── krb5.conf
```

### 5.3. Rename the krb5.conf to old.krb5.conf

```
cd ~/kafka-hdi-hol
mv krb5.conf old-krb5.conf
```

### 5.4. Lets create a new krb5.conf

```
cd ~/kafka-hdi-hol
vi krb5.conf 
```

Paste this & save-
```
[libdefaults]
        default_realm = AADDS.JRSMYDOMAIN.COM


[realms]
    AADDS.JRSMYDOMAIN.COM = {
                admin_server = aadds.jrsmydomain.com
                kdc = aadds.jrsmydomain.com
                default_domain = jrsmydomain.com
        }

[domain_realm]
    aadds.jrsmydomain.com = AADDS.JRSMYDOMAIN.COM
    .aadds.jrsmydomain.com = AADDS.JRSMYDOMAIN.COM


[login]
        krb4_convert = true
        krb4_get_tickets = false
```

Then go into this file and replace with your domain and realm specifics as detailed in old-krb5.conf

### 5.5. Create a Docker file

Start a file-
```
vi connect-worker-image-builder.dockerfile
```

Paste this into the file and save - be sure to edit it your UPN and domain realm.
```
FROM confluentinc/cp-kafka-connect:5.5.0
COPY kafka-sink-azure-kusto-1.0.1-jar-with-dependencies.jar /usr/share/java
COPY krb5.conf /etc/krb5.conf
COPY hdi-esp-jaas.conf /etc/hdi-esp-jaas.conf 
COPY kafka-client-hdi.keytab /etc/security/keytabs/kafka-client-hdi.keytab

ENV KAFKA_OPTS="-Djava.security.krb5.conf=/etc/krb5.conf"

ENV CONNECT_CONNECTOR_CLIENT_CONFIG_OVERRIDE_POLICY=All

ENV CONNECT_SASL_JAAS_CONFIG="com.sun.security.auth.module.Krb5LoginModule required useKeyTab=true storeKey=true keyTab=\"/etc/security/keytabs/kafka-client-hdi.keytab\" principal=\"hdiadminjrs@AADDS.JRSMYDOMAIN.COM\";"
ENV CONNECT_SASL_KERBEROS_SERVICE_NAME=kafka
ENV CONNECT_SASL_MECHANISM=GSSAPI
ENV CONNECT_SECURITY_PROTOCOL=SASL_PLAINTEXT
```

To connect ADX to Kafka via SSL, change the last variable, CONNECT_SECURITY_PROTOCOL, as follows:
```
ENV CONNECT_SECURITY_PROTOCOL=SASL_SSL
```

What we are doing above is taking the base Docker image from the ConfluentInc repo, copying the ADX jar to /usr/share/java and setting an environment variable to allow overrides at the consumer level, and including security configuration.

### 5.6. Create a Docker image off of the Docker file

Replace akhanolkar with your docker UID and run the below-
```
sudo docker build -t akhanolkar/kafka-connect-kusto-sink:2.0.0v1 -f connect-worker-image-builder.dockerfile .
```

List the images created-
```
docker image list
```

Author's output:
```
indra:kafka-confluentcloud-hol akhanolk$ docker image list
REPOSITORY                                    TAG                 IMAGE ID            CREATED             SIZE
akhanolkar/kafka-connect-kusto-sink           2.0.0v1             1870ace80b29        23 seconds ago      1.24GB
```

## 6. Push the image to Docker Hub

Run the command below, replacing akhanolkar with your Docker username-
```
docker push akhanolkar/kafka-connect-kusto-sink:2.0.0v1
```

Author's output-
```
indra:kafka-confluentcloud-hol akhanolk$ docker push akhanolkar/kafka-connect-kusto-sink:2.0.0v1
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

## 7. Clone KafkaConnect helm charts from Confluent git repo & make necessary edits

### 7.1. Clone the repo and copy what is required
```
cd ~
git clone https://github.com/confluentinc/cp-helm-charts.git

cd ~/kafka-hdi-hol
cp -R ~/cp-helm-charts/charts/cp-kafka-connect .
```

### 7.2. A quick browse

```
indra:kafka-hdi-hol akhanolk$ tree cp-kafka-connect/
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

### 7.3. Update values.yaml as follows

We need to update the values.yaml with the following-<br>
1. Replica count
```
replicaCount: 6
```

2. Image<br>
Your docker ID, instead of akhanolkar
```
image: akhanolkar/kafka-connect-kusto-sink
imageTag: 1.0.1v1
```
3. Kafka bootstrap servers<br>
Replace "yourBootStrapServerList" with your HDInsight Kafka bootstrap server loadbalancer FQDN:Port
```
kafka:
  bootstrapServers: "yourBootStrapServerList"
 ```
E.g. the author's bootstrap server entry is-
```
kafka:
  bootstrapServers: "nnn-nnnn.eastus2.azure.confluent.cloud:9092"
```

4. Set prometheous jmx monitoring to false as shown below-
```
prometheus:
  ## JMX Exporter Configuration
  ## ref: https://github.com/prometheus/jmx_exporter
  jmx:
    enabled: false
```

5.  Save
<br><br>

Here is the author's sample
```
# Default values for cp-kafka-connect.
# This is a YAML-formatted file.
# Declare variables to be passed into your templates.

replicaCount: 6

## Image Info
## ref: https://hub.docker.com/r/confluentinc/cp-kafka/
#image: confluentinc/cp-kafka-connect
#imageTag: 5.5.0

image: akhanolkar/kafka-connect-kusto-sink-hdi-esp
imageTag: 1.0.1v10


## Specify a imagePullPolicy
## ref: http://kubernetes.io/docs/user-guide/images/#pre-pulling-images
imagePullPolicy: IfNotPresent

## Specify an array of imagePullSecrets.
## Secrets must be manually created in the namespace.
## ref: https://kubernetes.io/docs/concepts/containers/images/#specifying-imagepullsecrets-on-a-pod
imagePullSecrets:

servicePort: 8083

## Kafka Connect properties
## ref: https://docs.confluent.io/current/connect/userguide.html#configuring-workers
configurationOverrides:
  "plugin.path": "/usr/share/java,/usr/share/confluent-hub-components"
  "key.converter": "io.confluent.connect.avro.AvroConverter"
  "value.converter": "io.confluent.connect.avro.AvroConverter"
  "key.converter.schemas.enable": "false"
  "value.converter.schemas.enable": "false"
  "internal.key.converter": "org.apache.kafka.connect.json.JsonConverter"
  "internal.value.converter": "org.apache.kafka.connect.json.JsonConverter"
  "config.storage.replication.factor": "3"
  "offset.storage.replication.factor": "3"
  "status.storage.replication.factor": "3"

## Kafka Connect JVM Heap Option
heapOptions: "-Xms512M -Xmx512M"

## Additional env variables
## CUSTOM_SCRIPT_PATH is the path of the custom shell script to be ran mounted in a volume
customEnv: {}
  # CUSTOM_SCRIPT_PATH: /etc/scripts/create-connectors.sh

resources: {}
  # We usually recommend not to specify default resources and to leave this as a conscious
  # choice for the user. This also increases chances charts run on environments with little
  # resources, such as Minikube. If you do want to specify resources, uncomment the following
  # lines, adjust them as necessary, and remove the curly braces after 'resources:'.
  # limits:
  #  cpu: 100m
  #  memory: 128Mi
  # requests:
  #  cpu: 100m
  #  memory: 128Mi

## Custom pod annotations
podAnnotations: {}

## Node labels for pod assignment
## Ref: https://kubernetes.io/docs/concepts/configuration/assign-pod-node/
nodeSelector: {}

## Taints to tolerate on node assignment:
## Ref: https://kubernetes.io/docs/concepts/configuration/taint-and-toleration/
tolerations: []

## Monitoring
## Kafka Connect JMX Settings
## ref: https://kafka.apache.org/documentation/#connect_monitoring
jmx:
  port: 5555

## Prometheus Exporter Configuration
## ref: https://prometheus.io/docs/instrumenting/exporters/
prometheus:
  ## JMX Exporter Configuration
  ## ref: https://github.com/prometheus/jmx_exporter
  jmx:
    enabled: false
    image: solsson/kafka-prometheus-jmx-exporter@sha256
    imageTag: 6f82e2b0464f50da8104acd7363fb9b995001ddff77d248379f8788e78946143
    imagePullPolicy: IfNotPresent
    port: 5556

    ## Resources configuration for the JMX exporter container.
    ## See the `resources` documentation above for details.
    resources: {}

## You can list load balanced service endpoint, or list of all brokers (which is hard in K8s).  e.g.:
## bootstrapServers: "PLAINTEXT://dozing-prawn-kafka-headless:9092"
kafka:
  bootstrapServers: "wn0-jrs03a.aadds.jrsmydomain.com:9092,wn1-jrs03a.aadds.jrsmydomain.com:9092,wn3-jrs03a.aadds.jrsmydomain.com:9092,wn2-jrs03a.aadds.jrsmydomain.com:9092"

## If the Kafka Chart is disabled a URL and port are required to connect
## e.g. gnoble-panther-cp-schema-registry:8081
cp-schema-registry:
  url: ""

## List of volumeMounts for connect server container
## ref: https://kubernetes.io/docs/concepts/storage/volumes/
volumeMounts:
# - name: credentials
#   mountPath: /etc/creds-volume

## List of volumeMounts for connect server container
## ref: https://kubernetes.io/docs/concepts/storage/volumes/
volumes:
# - name: credentials
#   secret:
#     secretName: creds

## Secret with multiple keys to serve the purpose of multiple secrets
## Values for all the keys will be base64 encoded when the Secret is created or updated
## ref: https://kubernetes.io/docs/concepts/configuration/secret/
secrets:
  # username: kafka123
  # password: connect321

## These values are used only when "customEnv.CUSTOM_SCRIPT_PATH" is defined.
## "livenessProbe" is required only for the edge cases where the custom script to be ran takes too much time
## and errors by the ENTRYPOINT are ignored by the container
## As an example such a similar script is added to "cp-helm-charts/examples/create-connectors.sh"
## ref: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
livenessProbe:
  # httpGet:
  #   path: /connectors
  #   port: 8083
  # initialDelaySeconds: 30
  # periodSeconds: 5
  # failureThreshold: 10
```

To connect ADX to Kafka via SSL, change:
1.  The volumeMounts, volumes and secrets sections in values.yaml 
2.  The data section in secrets.yaml
3.  The env section in deployment.yaml
4.  The sink properties sent via REST when provisioning the connector (covered later)

Specifically, in values.yaml (1):
```
volumeMounts
- name: secrets-vol
  mountPath: /etc/kafka/secrets

volumes
  - name: secrets-vol
    secret:
      secretName: ssl-config

secrets:
  kafka.connect.truststore.jks: [base64-encoded truststore that includes the public certificate(s) from the worker node(s)' keystore(s)]
  truststore-creds: [base64 encoded truststore password]
```

In secrets.yaml (2), remove the base64 encoding to allow the JKS to be kept in the values.yaml already encoded, so that the data section looks as follows:
```
data:
  {{- range $key, $value := .Values.secrets }}
  {{ $key }}: {{ $value }}
  {{- end }}
```

In deployment.yaml (3), add the following environment variables to spec.template.spec.containers.env:
```
- name: CONNECT_SECURITY_PROTOCOL
  value: SASL_SSL
- name: CONNECT_SSL_TRUSTSTORE_LOCATION
  value: /etc/kafka/secrets/kafka.connect.truststore.jks
- name: CONNECT_SSL_TRUSTSTORE_PASSWORD
  value: [the_truststore_password]
- name: CONNECT_PRODUCER_SECURITY_PROTOCOL
  value: SASL_SSL
- name: CONNECT_PRODUCER_SSL_TRUSTSTORE_LOCATION
  value: /etc/kafka/secrets/kafka.connect.truststore.jks
- name: CONNECT_PRODUCER_SSL_TRUSTSTORE_PASSWORD
  value: [the_truststore_password]
- name: CONNECT_CONSUMER_SECURITY_PROTOCOL
  value: SASL_SSL
- name: CONNECT_CONSUMER_SSL_TRUSTSTORE_LOCATION
  value: /etc/kafka/secrets/kafka.connect.truststore.jks
- name: CONNECT_CONSUMER_SSL_TRUSTSTORE_PASSWORD
  value: [the_truststore_password]
```
These are examples of the [values.yaml](yamls/values.yaml), [secrets.yaml](yamls/secrets.yaml) and [deployment.yaml](yamls/deployment.yaml).


## 8. Provision KafkaConnect workers on our Azure Kubernetes Service cluster

### 8.1. Login to Azure CLI & set the subscription to use
[Install the CLI if it does not exist.](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
<br>

1. Login
```
az login
```
This will launch the Azure portal, sign-in dialog.  Sign-in.<br>


2. Switch to the right Azure subscription in case you have multiple
```
az account set --subscription YOUR_SUBSCRIPTION_GUID
```

3.  Get the AKS cluster admin acccess with this command<br>
If you have named your cluster differently, be sure to replace accordingly-
```
az aks get-credentials --resource-group YOUR_RESOURCE_GROUP --name YOUR_CLUSTER --admin
```

Author's output-
```
indra:kafka-confluentcloud-hol akhanolk$ az aks get-credentials --resource-group kafka-hdi-rg --name connector-k8s-cluster --admin
Merged "connector-k8s-cluster-admin" as current context in /Users/akhanolk/.kube/config
```

### 8.2. Provision KafkaConnect on AKS

Run the below-
```
helm install ./cp-kafka-connect --generate-name
```

Author's output-
```
indra:kafka-hdi-hol akhanolk$ helm install ./cp-kafka-connect --generate-name
NAME: cp-kafka-connect-1598073371
LAST DEPLOYED: Sat Aug 22 00:16:13 2020
NAMESPACE: default
STATUS: deployed
REVISION: 1
TEST SUITE: None
NOTES:
This chart installs a Confluent Kafka Connect

https://docs.confluent.io/current/connect/index.html
```

### 8.3. Check pods
Run the below-
```
kubectl get pods
```

Author's output-
```
indra:kafka-confluentcloud-hol akhanolk$ kubectl get pods
NAME                                           READY   STATUS    RESTARTS   AGE
cp-kafka-connect-1598109267-76465bff44-7s9vs   1/1     Running   0          5m27s
cp-kafka-connect-1598109267-76465bff44-9btwt   1/1     Running   0          5m27s
cp-kafka-connect-1598109267-76465bff44-j4pbq   1/1     Running   0          5m27s
cp-kafka-connect-1598109267-76465bff44-rp5kt   1/1     Running   0          5m27s
cp-kafka-connect-1598109267-76465bff44-wv5w2   1/1     Running   0          5m27s
cp-kafka-connect-1598109267-76465bff44-x7rlm   1/1     Running   0          5m27s
```

### 8.4. Check service 

Run the below-
```
kubectl get svc
```

Author's output -
```
indra:kafka-confluentcloud-hol akhanolk$ kubectl get svc
NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)    AGE
cp-kafka-connect-1598109267   ClusterIP   10.0.146.166   <none>        8083/TCP   5m52s
kubernetes                    ClusterIP   10.0.0.1       <none>        443/TCP    2d23h
```

This is the service name- cp-kafka-connect-1598109267 

### 8.5. SSH into a pod

Pick one pod from your list of 6 in #6.3<br>
Here is the author's command and output-
```
kubectl exec -it cp-kafka-connect-1598073371-6676d5b5bd-7sbzn -- bash
```

#### 8.5.1.  Check processes running

```
ps -ef
```

Author's output-
```
root@cp-kafka-connect-1598109267-76465bff44-7s9vs:/# ps -ef
UID         PID   PPID  C STIME TTY          TIME CMD
root          1      0  5 15:14 ?        00:01:19 java -Xms512M -Xmx512M -server -XX:+UseG1GC -XX:MaxGCPauseMillis=20 -XX:InitiatingHeapOccupancyPercent=35 -XX:+Expl
root        186      0  0 15:15 pts/0    00:00:00 bash
root        220    186  0 15:40 pts/0    00:00:00 ps -ef
```

#### 8.5.2.  Check /usr/share/jave to see if the ADX/Kusto jar is there

Command-
```
ls -l /usr/share/java
```
Author's output-
```
root@cp-kafka-connect-1598109267-76465bff44-7s9vs:/# ls -l /usr/share/java
total 10636
drwxr-xr-x 2 root root     4096 Apr 18 17:23 acl
drwxr-xr-x 2 root root     4096 Apr 18 17:22 confluent-common
drwxr-xr-x 2 root root    12288 Apr 18 17:23 confluent-control-center
drwxr-xr-x 2 root root     4096 Apr 18 17:23 confluent-hub-client
drwxr-xr-x 2 root root    12288 Apr 18 17:23 confluent-rebalancer
-rw-r--r-- 1 root root      957 May  6  2014 java_defaults.mk
drwxr-xr-x 1 root root     4096 Apr 18 17:23 kafka
drwxr-xr-x 2 root root     4096 Apr 18 17:24 kafka-connect-activemq
drwxr-xr-x 2 root root     4096 Apr 18 17:24 kafka-connect-elasticsearch
drwxr-xr-x 2 root root     4096 Apr 18 17:24 kafka-connect-ibmmq
drwxr-xr-x 2 root root     4096 Apr 18 17:24 kafka-connect-jdbc
drwxr-xr-x 2 root root     4096 Apr 18 17:24 kafka-connect-jms
drwxr-xr-x 2 root root     4096 Apr 18 17:24 kafka-connect-s3
drwxr-xr-x 2 root root     4096 Apr 18 17:24 kafka-connect-storage-common
drwxr-xr-x 2 root root     4096 Apr 18 17:22 kafka-serde-tools
-rw-r--r-- 1 root root 10797367 Aug  4 13:24 kafka-sink-azure-kusto-1.0.1-jar-with-dependencies.jar
drwxr-xr-x 2 root root     4096 Apr 18 17:23 monitoring-interceptors
drwxr-xr-x 2 root root     4096 Apr 18 17:22 rest-utils
drwxr-xr-x 2 root root     4096 Apr 18 17:22 schema-registry
```

### 8.5.3.  Check if the environment conigs we applied in the docker file are available..
Run the command-
```
printenv | sort
```


Author's output-
```
ALLOW_UNSIGNED=false
COMPONENT=kafka-connect
CONFLUENT_DEB_VERSION=1
CONFLUENT_PLATFORM_LABEL=
CONFLUENT_VERSION=5.5.0
CONNECT_BOOTSTRAP_SERVERS=wn0-jrs03a.aadds.jrsmydomain.com:9092,wn1-jrs03a.aadds.jrsmydomain.com:9092,wn3-jrs03a.aadds.jrsmydomain.com:9092,wn2-jrs03a.aadds.jrsmydomain.com:9092
CONNECT_CONFIG_STORAGE_REPLICATION_FACTOR=3
CONNECT_CONFIG_STORAGE_TOPIC=cp-kafka-connect-1598575381-config
CONNECT_CONNECTOR_CLIENT_CONFIG_OVERRIDE_POLICY=All
CONNECT_GROUP_ID=cp-kafka-connect-1598575381
CONNECT_INTERNAL_KEY_CONVERTER=org.apache.kafka.connect.json.JsonConverter
CONNECT_INTERNAL_VALUE_CONVERTER=org.apache.kafka.connect.json.JsonConverter
CONNECT_KEY_CONVERTER=io.confluent.connect.avro.AvroConverter
CONNECT_KEY_CONVERTER_SCHEMAS_ENABLE=false
CONNECT_KEY_CONVERTER_SCHEMA_REGISTRY_URL=http://cp-kafka-connect-1598575381-cp-schema-registry:8081
CONNECT_OFFSET_STORAGE_REPLICATION_FACTOR=3
CONNECT_OFFSET_STORAGE_TOPIC=cp-kafka-connect-1598575381-offset
CONNECT_PLUGIN_PATH=/usr/share/java,/usr/share/confluent-hub-components
CONNECT_REST_ADVERTISED_HOST_NAME=10.0.0.141
CONNECT_SASL_JAAS_CONFIG=com.sun.security.auth.module.Krb5LoginModule required useKeyTab=true storeKey=true keyTab="/etc/security/keytabs/kafka-client-hdi.keytab" principal="hdiadminjrs@AADDS.JRSMYDOMAIN.COM";
CONNECT_SASL_KERBEROS_SERVICE_NAME=kafka
CONNECT_SASL_MECHANISM=GSSAPI
CONNECT_SECURITY_PROTOCOL=SASL_PLAINTEXT
CONNECT_STATUS_STORAGE_REPLICATION_FACTOR=3
CONNECT_STATUS_STORAGE_TOPIC=cp-kafka-connect-1598575381-status
CONNECT_VALUE_CONVERTER=io.confluent.connect.avro.AvroConverter
CONNECT_VALUE_CONVERTER_SCHEMAS_ENABLE=false
CONNECT_VALUE_CONVERTER_SCHEMA_REGISTRY_URL=http://cp-kafka-connect-1598575381-cp-schema-registry:8081
CP_KAFKA_CONNECT_1598575381_PORT=tcp://10.10.253.124:8083
CP_KAFKA_CONNECT_1598575381_PORT_8083_TCP=tcp://10.10.253.124:8083
CP_KAFKA_CONNECT_1598575381_PORT_8083_TCP_ADDR=10.10.253.124
CP_KAFKA_CONNECT_1598575381_PORT_8083_TCP_PORT=8083
CP_KAFKA_CONNECT_1598575381_PORT_8083_TCP_PROTO=tcp
CP_KAFKA_CONNECT_1598575381_SERVICE_HOST=10.10.253.124
CP_KAFKA_CONNECT_1598575381_SERVICE_PORT=8083
CP_KAFKA_CONNECT_1598575381_SERVICE_PORT_KAFKA_CONNECT=8083
CUB_CLASSPATH=/etc/confluent/docker/docker-utils.jar
HOME=/root
HOSTNAME=cp-kafka-connect-1598575381-b4cf47488-2p47l
KAFKA_ADVERTISED_LISTENERS=
KAFKA_HEAP_OPTS=-Xms512M -Xmx512M
KAFKA_JMX_PORT=5555
KAFKA_OPTS=-Djava.security.krb5.conf=/etc/krb5.conf
KAFKA_VERSION=
KAFKA_ZOOKEEPER_CONNECT=
KUBERNETES_PORT=tcp://10.10.0.1:443
KUBERNETES_PORT_443_TCP=tcp://10.10.0.1:443
KUBERNETES_PORT_443_TCP_ADDR=10.10.0.1
KUBERNETES_PORT_443_TCP_PORT=443
KUBERNETES_PORT_443_TCP_PROTO=tcp
KUBERNETES_SERVICE_HOST=10.10.0.1
KUBERNETES_SERVICE_PORT=443
KUBERNETES_SERVICE_PORT_HTTPS=443
LANG=C.UTF-8
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PWD=/
PYTHON_PIP_VERSION=8.1.2
PYTHON_VERSION=2.7.9-1
SCALA_VERSION=2.12
SHLVL=1
TERM=xterm
ZULU_OPENJDK_VERSION=8=8.38.0.13
_=/usr/bin/printenv
```
The following should be there-
```
CONNECT_CONNECTOR_CLIENT_CONFIG_OVERRIDE_POLICY=All
CONNECT_SASL_JAAS_CONFIG=com.sun.security.auth.module.Krb5LoginModule required useKeyTab=true storeKey=true keyTab="/etc/security/keytabs/kafka-client-hdi.keytab" principal="UPN@YOUR_REALM";
CONNECT_SASL_MECHANISM=GSSAPI
CONNECT_SECURITY_PROTOCOL=SASL_PLAINTEXT
CONNECT_SASL_KERBEROS_SERVICE_NAME=kafka
```

Now - exit root..
```
exit
```
### 8.5.4.  Lets check logs to see if there are any errors
Lets review the logs of one of the pods from 6.3

```
kubectl logs <podName>
```

If you see something like this, we are good to go...
```
[2020-08-22 15:15:20,337] INFO [Worker clientId=connect-1, groupId=cp-kafka-connect-1598109267] (Re-)joining group (org.apache.kafka.clients.consumer.internals.AbstractCoordinator)
[2020-08-22 15:15:20,376] INFO [Worker clientId=connect-1, groupId=cp-kafka-connect-1598109267] Join group failed with org.apache.kafka.common.errors.MemberIdRequiredException: The group member needs to have a valid member id before actually entering a consumer group (org.apache.kafka.clients.consumer.internals.AbstractCoordinator)
[2020-08-22 15:15:20,376] INFO [Worker clientId=connect-1, groupId=cp-kafka-connect-1598109267] (Re-)joining group (org.apache.kafka.clients.consumer.internals.AbstractCoordinator)
[2020-08-22 15:15:21,350] INFO [Worker clientId=connect-1, groupId=cp-kafka-connect-1598109267] Successfully joined group with generation 3 (org.apache.kafka.clients.consumer.internals.AbstractCoordinator)
[2020-08-22 15:15:21,352] INFO [Worker clientId=connect-1, groupId=cp-kafka-connect-1598109267] Joined group at generation 3 with protocol version 2 and got assignment: Assignment{error=0, leader='connect-1-1de302ef-1397-40b3-b108-925feef75d1a', leaderUrl='http://10.244.3.7:8083/', offset=1, connectorIds=[], taskIds=[], revokedConnectorIds=[], revokedTaskIds=[], delay=0} with rebalance delay: 0 (org.apache.kafka.connect.runtime.distributed.DistributedHerder)
[2020-08-22 15:15:21,352] WARN [Worker clientId=connect-1, groupId=cp-kafka-connect-1598109267] Catching up to assignment's config offset. (org.apache.kafka.connect.runtime.distributed.DistributedHerder)
[2020-08-22 15:15:21,352] INFO [Worker clientId=connect-1, groupId=cp-kafka-connect-1598109267] Current config state offset -1 is behind group assignment 1, reading to end of config log (org.apache.kafka.connect.runtime.distributed.DistributedHerder)
[2020-08-22 15:15:21,442] INFO [Worker clientId=connect-1, groupId=cp-kafka-connect-1598109267] Finished reading to end of log and updated config snapshot, new config log offset: 1 (org.apache.kafka.connect.runtime.distributed.DistributedHerder)
[2020-08-22 15:15:21,442] INFO [Worker clientId=connect-1, groupId=cp-kafka-connect-1598109267] Starting connectors and tasks using config offset 1 (org.apache.kafka.connect.runtime.distributed.DistributedHerder)
[2020-08-22 15:15:21,442] INFO [Worker clientId=connect-1, groupId=cp-kafka-connect-1598109267] Finished starting connectors and tasks (org.apache.kafka.connect.runtime.distributed.DistributedHerder)
```

### 8.6. Describe a pod to view details

Run the command below with a pod name from 6.3
```
kubectl describe pod YOUR_POD_NAME
```

Author's output-
```
indra:kafka-confluentcloud-hol akhanolk$ kubectl describe pod cp-kafka-connect-1598109267-76465bff44-7s9vs
Name:         cp-kafka-connect-1598109267-76465bff44-7s9vs
Namespace:    default
Priority:     0
Node:         aks-agentpool-23362501-vmss000005/10.240.0.9
Start Time:   Sat, 22 Aug 2020 10:14:30 -0500
Labels:       app=cp-kafka-connect
              pod-template-hash=76465bff44
              release=cp-kafka-connect-1598109267
Annotations:  <none>
Status:       Running
IP:           10.244.1.10
IPs:
  IP:           10.244.1.10
Controlled By:  ReplicaSet/cp-kafka-connect-1598109267-76465bff44
Containers:
  cp-kafka-connect-server:
    Container ID:   docker://f574c04da945ef986296a7ff341c277be9799e61d1c8702096d7ed792e8beb30
    Image:          akhanolkar/kafka-connect-kusto-sink:2.0.0v3
    Image ID:       docker-pullable://akhanolkar/kafka-connect-kusto-sink@sha256:65b7c05d5e795c7491d52a5e12636faa1f8f9b4a460a24ec081e6bf4047d405d
    Port:           8083/TCP
    Host Port:      0/TCP
    State:          Running
      Started:      Sat, 22 Aug 2020 10:14:32 -0500
    Ready:          True
    Restart Count:  0
    Environment:
      CONNECT_REST_ADVERTISED_HOST_NAME:             (v1:status.podIP)
      CONNECT_BOOTSTRAP_SERVERS:                    PLAINTEXT://nnn-nnnnn.eastus2.azure.confluent.cloud:9092
      CONNECT_GROUP_ID:                             cp-kafka-connect-1598109267
      CONNECT_CONFIG_STORAGE_TOPIC:                 cp-kafka-connect-1598109267-config
      CONNECT_OFFSET_STORAGE_TOPIC:                 cp-kafka-connect-1598109267-offset
      CONNECT_STATUS_STORAGE_TOPIC:                 cp-kafka-connect-1598109267-status
      CONNECT_KEY_CONVERTER_SCHEMA_REGISTRY_URL:    http://cp-kafka-connect-1598109267-cp-schema-registry:8081
      CONNECT_VALUE_CONVERTER_SCHEMA_REGISTRY_URL:  http://cp-kafka-connect-1598109267-cp-schema-registry:8081
      KAFKA_HEAP_OPTS:                              -Xms512M -Xmx512M
      CONNECT_CONFIG_STORAGE_REPLICATION_FACTOR:    3
      CONNECT_INTERNAL_KEY_CONVERTER:               org.apache.kafka.connect.json.JsonConverter
      CONNECT_INTERNAL_VALUE_CONVERTER:             org.apache.kafka.connect.json.JsonConverter
      CONNECT_KEY_CONVERTER:                        io.confluent.connect.avro.AvroConverter
      CONNECT_KEY_CONVERTER_SCHEMAS_ENABLE:         false
      CONNECT_OFFSET_STORAGE_REPLICATION_FACTOR:    3
      CONNECT_PLUGIN_PATH:                          /usr/share/java,/usr/share/confluent-hub-components
      CONNECT_STATUS_STORAGE_REPLICATION_FACTOR:    3
      CONNECT_VALUE_CONVERTER:                      io.confluent.connect.avro.AvroConverter
      CONNECT_VALUE_CONVERTER_SCHEMAS_ENABLE:       false
      KAFKA_JMX_PORT:                               5555
    Mounts:
      /var/run/secrets/kubernetes.io/serviceaccount from default-token-p67xc (ro)
Conditions:
  Type              Status
  Initialized       True 
  Ready             True 
  ContainersReady   True 
  PodScheduled      True 
Volumes:
  default-token-p67xc:
    Type:        Secret (a volume populated by a Secret)
    SecretName:  default-token-p67xc
    Optional:    false
QoS Class:       BestEffort
Node-Selectors:  <none>
Tolerations:     node.kubernetes.io/not-ready:NoExecute for 300s
                 node.kubernetes.io/unreachable:NoExecute for 300s
Events:
  Type    Reason     Age   From                                        Message
  ----    ------     ----  ----                                        -------
  Normal  Scheduled  43m   default-scheduler                           Successfully assigned default/cp-kafka-connect-1598109267-76465bff44-7s9vs to aks-agentpool-23362501-vmss000005
  Normal  Pulling    43m   kubelet, aks-agentpool-23362501-vmss000005  Pulling image "akhanolkar/kafka-connect-kusto-sink:2.0.0v3"
  Normal  Pulled     43m   kubelet, aks-agentpool-23362501-vmss000005  Successfully pulled image "akhanolkar/kafka-connect-kusto-sink:2.0.0v3"
  Normal  Created    43m   kubelet, aks-agentpool-23362501-vmss000005  Created container cp-kafka-connect-server
  Normal  Started    43m   kubelet, aks-agentpool-23362501-vmss000005  Started container cp-kafka-connect-server
```

Points to note here are-
1.  The output of command "kubectl get svc" - the service ID is the group ID 
```
      CONNECT_GROUP_ID:                             cp-kafka-connect-1598109267
```
2.  Three special topics are created by KafkaConnect to maintain offsets of the connect tasks-
```
      CONNECT_CONFIG_STORAGE_TOPIC:                 cp-kafka-connect-1598109267-config
      CONNECT_OFFSET_STORAGE_TOPIC:                 cp-kafka-connect-1598109267-offset
      CONNECT_STATUS_STORAGE_TOPIC:                 cp-kafka-connect-1598109267-status
```
These are specific to the service ID from "kubectl get svc".  If you uninstall and reinstall KafkaConnect, you will see another set of 3 topics, identifiable by the service ID.

## 9. Start port forwarding to be able to make REST calls from your machine to KafkaConnect service running on AKS pods
You will need the service ID from the command "kubectl get svc".  Substitute it in the below command.

```
sudo kubectl port-forward svc/YOUR_SERVICE_ID 803:8083
```

Author's output-
```
indra:kafka-confluentcloud-hol akhanolk$ sudo kubectl port-forward svc/cp-kafka-connect-1598109267 803:8083
Forwarding from 127.0.0.1:803 -> 8083
Forwarding from [::1]:803 -> 8083
.....
```
Keep this session alive when you need to manipulate the ADX connectors.

## 10. Download & install Postman

[Install Postman](https://www.postman.com/downloads/) if you dont already have it.

## 11. Import the Postman JSON collection with KafkaConnect REST API call samples

### 11.1. Download the Postman collection for the lab 

Download [this](https://github.com/Azure/azure-kusto-labs/blob/confluent-clound-hol/kafka-integration/confluent-cloud/rest-calls/Confluent-Cloud-ADX-HoL-1-STUB.postman_collection.json) to you local machine.<br>
We will import this into Postman.  Its a stub with all the REST calls pre-created.


### 11.2. Launch Postman and click on the import button

![POSTMAN](images/05-CONNECTOR-01.png)
<br>
<br>
<hr>
<br>

Click on the import button and import from the file dowloaded in 9.1.

![POSTMAN](images/05-CONNECTOR-01-2.png)
<br>
<br>
<hr>
<br>


### 11.3. View available connector plugins

![POSTMAN](images/05-CONNECTOR-02.png)
<br>
<br>
<hr>
<br>

### 11.4. Check if the ADX/Kusto connector is already provisioned

![POSTMAN](images/05-CONNECTOR-03.png)
<br>
<br>
<hr>
<br>

### 11.5. Provision the connector after editing the body of the REST call to match your configuration

![POSTMAN](images/05-CONNECTOR-04.png)
<br>
<br>
<hr>
<br>

You will need the following details-
```
{
    "name": "KustoSinkConnectorCrimes",
    "config": {
        "connector.class": "com.microsoft.azure.kusto.kafka.connect.sink.KustoSinkConnector",
        "topics": "crimes",
        "kusto.ingestion.url":"YOUR-ADX-INGEST-URL",
        "kusto.query.url":"YOUR-ADX-QUERY-URL",
        "aad.auth.authority": "YOUR-AAD-TENANT-ID",
        "aad.auth.appid":"YOUR-ADD-SPN-APP-ID",
        "aad.auth.appkey":"YOUR-AAD-SPN-SECRET",
        "kusto.tables.topics.mapping": "[{'topic': 'crimes','db': 'crimes_db', 'table': 'crimes','format': 'json', 'mapping':'crimes_mapping'}]", 
        "key.converter": "org.apache.kafka.connect.storage.StringConverter",
        "value.converter": "org.apache.kafka.connect.storage.StringConverter",
        "tasks.max": "6",
        "tempdir.path":"/var/tmp/",
        "flush.size.bytes":"10485760",
        "flush.interval.ms": "15000",
        "behavior.on.error": "LOG",        
        "consumer.override.bootstrap.servers": "BOOTSTRAP-SERVER:PORT-CSV",
        "consumer.override.security.protocol": "SASL_PLAINTEXT",
        "consumer.override.sasl.mechanism": "GSSAPI",
        "consumer.override.sasl.kerberos.service.name": "kafka",
        "consumer.override.sasl.jaas.config": "com.sun.security.auth.module.Krb5LoginModule required useKeyTab=true storeKey=true keyTab=\"/etc/security/keytabs/kafka-client-hdi.keytab\" principal=\"UPN-NAME@REALM\";",
        "consumer.override.request.timeout.ms": "20000",
        "consumer.override.retry.backoff.ms": "500"
    }
}
```
To connect ADX to Kafka via SSL, the final step (4) is to change "consumer.override.security.protocol" from "SASL_PLAINTEXT" to "SASL_SSL", and to add the following:
```
"consumer.override.ssl.endpoint.identification.algorithm": "https"
```


Making this REST API call will actually launch copy tasks on your KafkaConnect workers.  We have a 1:1 ratio (1 AKS node = 1 KafkaConnect pod = 1 connector task)
but depending on resources, you can oversubcribe and add more tasks.

IDEALLY, you want as many tasks as Kafka topic partitions.

### 11.6. View configuration of connector tasks provisioned already, if any

![POSTMAN](images/05-CONNECTOR-05.png)
<br>
<br>
<hr>
<br>

### 11.7. View status of connector tasks provisioned 

![POSTMAN](images/05-CONNECTOR-06.png)
<br>
<br>
<hr>
<br>

### 11.8. Pause connectors should you need to

![POSTMAN](images/05-CONNECTOR-07.png)
<br>
<br>
<hr>
<br>

### 11.9. Resume connectors paused previously

![POSTMAN](images/05-CONNECTOR-08.png)
<br>
<br>
<hr>
<br>

### 11.10. List all individual connector tasks with status

![POSTMAN](images/05-CONNECTOR-09.png)
<br>
<br>
<hr>
<br>

### 11.11. Restart connectors when needed

![POSTMAN](images/05-CONNECTOR-10.png)
<br>
<br>
<hr>
<br>

### 11.12. Delete connectors altogether

![POSTMAN](images/05-CONNECTOR-11.png)
<br>
<br>
<hr>
<br>

<br><br><hr>
This concludes this module. You can now proceed to the [next and last module](../../confluent-cloud/6-run-e2e.md), where we will run an end to end test.

## 12. Validate data delivery in Azure Data Explorer

Launching the connector tasks in [section 11.5](connectors-crud-esp.md#115-provision-the-connector-after-editing-the-body-of-the-rest-call-to-match-your-configuration) starts the copy process.

<br>
This concludes this module.
