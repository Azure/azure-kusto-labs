#### KAFKA INTEGRATION LAB SERIES

<hr>

# About

This set of labs details using the Kafka connector thorough example, in a distributed mode (on k8s containers), with two flavors of Kafka - <br>
1. HDInsight 4.0 (Kafka 2.1 at the time of authoring) and<br>
2. Confluent Platform 5.5.0 with operator for k8s (Kafka 2.5 at the time of authoring)

# Lab resources

The resources used in the lab are-
### 1) Azure Data Explorer cluster
- Vnet injected ADX

### 2) Azure Databricks cluster
- Vnet injected Spark cluster for Spark connector testing, and to generate load for Kafka

### 3) HDInsight Kafka
- Vnet injected HDInsight Kafka (VMs)
- Kusto Kafka connectors on AKS for HDInsight Kafka

![HDI](images/HDI-E2E.png)

### 4) Confluent Kafka
- Vnet injected Confluent Kafka (AKS)
- Kusto Kafka connectors on the same Confluent Kafka cluster on dedicated nodes

# Provision foundational resources for the labs 

This includes-
1.  Resource group
2.  Virtual network
3.  Subnets
4.  Service Principal
5.  Azure Data Explorer
6.  Storage Account v2
7.  Azure Databricks + import code for downloading public dataset and publishing to Kafka

Details are [here.](common/README.md)

# Set up your machine for the lab
You will need the following:
1. Postman
2. Optionally - Windows subsystem for Linux; All commands in the lab assume you are using Linux
3. Azure CLI
4. Azure AKS CLI
5. Helm
6. Docker

Details are [here.](common/conf-dev-machine.md)

# Start the labs

1.  [Distributed KafkaConnect with Confluent Platform 5.5.0 on Azure Kubernetes Service](https://github.com/Azure/azure-kusto-labs/blob/master/kafka-integration/distributed-mode/confluent-kafka/README.md)
2.  Distributed KafkaConnect with HDInsight Kafka 4.0, and connectors on Azure Kubernetes Service
