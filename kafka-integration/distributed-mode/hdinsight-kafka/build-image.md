##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with HDInsight](README.md)
<hr>


# 1. FOCUS: BUILD docker image and publish to docker hub

This module details docker image build of the KafkaConnect Kusto sink connector and publish to DockerHub.

## 1. Create a directory 

```
mkdir -p ~/opt/kafka/docker-image-build
```
## 2. Download the Kusto sink connector

```
wget "https://github.com/Azure/kafka-sink-azure-kusto/releases/download/0.3.4/kafka-sink-azure-kusto-0.3.4-jar-with-dependencies.jar"
```

## 3. Docker login

Login to docker, with your UID and password
```
docker login --username akhanolkar
```

## 4. Create DockerFile

```
vi connector-image-builder.dockerfile
```

Paste this into the file and save..
```
FROM confluentinc/cp-kafka-connect:5.5.0
COPY kafka-sink-azure-kusto-0.3.4-jar-with-dependencies.jar /usr/share/java
```

## 5. Build docker image

```
sudo docker build -t akhanolkar/kafka-connect-kusto-sink:0.3.4v1 -f connector-image-builder.dockerfile .
```
Output..
```
Sending build context to Docker daemon  60.11MB
Step 1/2 : FROM confluentinc/cp-kafka-connect:5.5.0
5.5.0: Pulling from confluentinc/cp-kafka-connect
3707da5d6610: Pull complete 
dba8c1d87339: Pull complete 
d3d8e9b13a8a: Pull complete 
94b37b8de5ff: Pull complete 
852636014dd8: Pull complete 
ef0a129708c8: Pull complete 
f365c2c2d58f: Pull complete 
9d0a1d7ef2c2: Pull complete 
21bbaf9cc0a5: Pull complete 
1c8a294142e6: Pull complete 
Digest: sha256:7444aa5be76d4b49b66abdf732ceab0ada2fee095d4f004dbaa6437dc9f3dc37
Status: Downloaded newer image for confluentinc/cp-kafka-connect:5.5.0
 ---> 98e4bcc7d318
Step 2/2 : COPY kafka-sink-azure-kusto-0.3.4-jar-with-dependencies.jar /usr/share/java
 ---> ec6d27564792
Successfully built ec6d27564792
Successfully tagged akhanolkar/kafka-connect-kusto-sink:0.3.4v1
```

## 5. Check locally, for the image

```
docker images | grep 0.3.4v1
```

Output should be like this..
```
akhanolkar/kafka-connect-kusto-sink   0.3.4v1             ec6d27564792        About a minute ago   1.24GB
```

## 6.  Push to Docker Hub - use your own login

Login..using your own UID
```
docker login -u "akhanolkar" -p "<My password>" docker.io
```
Push...with your ID
```
docker push akhanolkar/kafka-connect-kusto-sink:0.3.4v1
```

Output..
```
The push refers to repository [docker.io/akhanolkar/kafka-connect-kusto-sink]
b3aa51c20e65: Pushed 
c20428756bff: Mounted from confluentinc/cp-kafka-connect 
75cd0f16c778: Mounted from confluentinc/cp-kafka-connect 
b1aa21789e59: Mounted from confluentinc/cp-kafka-connect 
0d9a93e8c391: Mounted from confluentinc/cp-kafka-connect 
05c69d782ee2: Mounted from confluentinc/cp-kafka-connect 
fb73194a06ee: Mounted from confluentinc/cp-kafka-connect 
bc537b2bbfd6: Mounted from confluentinc/cp-kafka-connect 
0818dd46b53a: Mounted from confluentinc/cp-kafka-connect 
19e377f490b1: Mounted from confluentinc/cp-kafka-connect 
a8ff4211732a: Mounted from confluentinc/cp-kafka-connect 
0.3.4v1: digest: sha256:493b3eac1fa2aa513b27ca88ff108670a3fe5409a58a4d6a2b37cf872718575a size: 2640
```

This concludes the module.

<hr>

[Distributed Kafka ingestion with HDInsight](README.md)
