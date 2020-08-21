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


The process to create the image is as follows-
