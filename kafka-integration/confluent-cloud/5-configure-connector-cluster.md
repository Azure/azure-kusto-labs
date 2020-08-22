# About

This module covers the following steps that essentially sets the stage for integration-
1.  Create a Docker Hub account if it does not exist
2.  Install Docker desktop on your machine
3.  Building a docker image for the KafkaConnect worker that include any connect worker level configurations, and the ADX connector jar
4.  Push the image to the Docker hub
5.  Provision KafkaConnect workers on our Azure Kubernetes Service cluster
6.  Install Postman on our local machine
7.  Import KafkaConnect REST call JSON collection from Github into Postman
8.  Launch the Kafka-ADX copy tasks, otherwise called connector tasks

## 1.  Create a Docker Hub account

Follow the instructions [here](https://hub.docker.com/signup) and create an account.  Note down your user ID and password.

## 2.  Install Docker desktop on your machine and launch it

Follow the instructions [here](https://www.docker.com/products/docker-desktop) and complete the installation and start the service.

## 3. Create a local directory

In linux/Mac-
```
cd ~
mkdir kafka-confluentcloud-hol
cd kafka-confluentcloud-hol
```

## 4. Download the ADX connector jar
Run the following commands-<br>

1.  Switch directories if needed
```
cd ~/kafka-confluentcloud-hol
```
2.  Download the jar
```
wget https://github.com/Azure/kafka-sink-azure-kusto/releases/download/v1.0.1/kafka-sink-azure-kusto-1.0.1-jar-with-dependencies.jar 
```

