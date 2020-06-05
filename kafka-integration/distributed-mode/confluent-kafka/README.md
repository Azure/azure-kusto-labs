#### KAFKA INTEGRATION LAB SERIES

[Menu for distributed Kafka ingestion](../README.md)
<hr>

# 1. About

This is the home page of the ADX Kafka ingestion lab in distributed mode with Confluent Platform for Kafka.
It covers:
1.  Provisioning Confluent Platform on AKS
2.  Publishing events to Kafka from Spark on Azure Databricks
3.  Consuming from Kafka and sinking to ADX with KafkaConnect ADX connector plugin

This is a lengthy lab, dedicate 8-16 hours for this hands on lab if you are ne to Azure and all the distributed systems featured in this lab.

# 2. Pre-requisites

This lab required the foundational resources provisioned, as detailed [here.](../common/README.md)

# 3. Provision an Azure Kubernetes Service cluster
The Azure Kubernetes Cluster (AKS) will serve as the underlying infrastructure for Kafka.  Details for provisioning are [here.](create-aks.md)

# 4. Download Confluent operator and edit configuration files 
We will download Confluent operator locally on your developer machine and edit confirguation files as needed for the lab.  <br>
Details are [here.](download-operator.md)

# 5. Create a Docker image of Confluent operator with the ADX KafkaConnect jar and publish to Docker hub
1. We will create a Docker image that includes the Confluent operator for Connect, and the ADX KafkaConnect connector jar, and publish to Docker hub.
2.  We will edit our Azure specific YAML from #4 to leverage this new Docker image

Details are [here.](bake-connector-image.md)


# 6. Install Confluent platform on AKS
The following are the steps-
1.  Install [Confluent operator](install-operator.md)
2.  Install [Zookeeper service](install-zookeeper.md)
3.  Install [Broker service](install-broker.md)
4.  Install [Confluent Control Center](install-control-center.md)
5.  Create a [Kafka topic](create-kafka-topic.md)
6.  Produce to the Kafka topic from [Spark](produce-to-kafka.md)

# 7. Integrate from Kafka to ADX





