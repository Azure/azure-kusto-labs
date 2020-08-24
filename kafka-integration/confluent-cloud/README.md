# Hands-on-Lab: Azure Data Explorer integration with Kafka on Confluent Cloud managed PaaS

This lab details usage of self-managed Azure Data Explorer KafkaConnect sink connector with Confluent Cloud on Azure.<br>

## Pictorial overview of the lab

![RG](images/E2E.png)
<br>
<br>
<hr>
<br>

## Lab summary

The lab showcases very basic Kafka ingestion into ADX. It does not show case a real time usecase, and does not include some of the streaming capabilities of Confluent Cloud and Kafka in general to keep the lab simple and **Azure Data Explorer integration** focused.<br>

Essentially there are the below aspects to the lab-<br>
### 1.  The data
We will use the Chicago crimes public dataset.  It is about 7 million records.<br>

### 2. Kafka on Azure
We will leverage Confluent Cloud on Azure

### 3. Kafka producer
We will use Spark on Databricks to publish to Kafka, as its a PaaS, easy to provision and use, for the simplicity of use of notebooks, and the distributed nature and the robust integration of Spark with Kafka.  

### 4. KafkaConnect cluster for integration
We will use Azure Kubernetes Service (AKS), collectively AKS and Kubernetes in general make a great platform for distributed KafkaConnect.

### 5. Azure Data Explorer cluster as the sink
For the purpose of simplicity, we will use a cluster that is not in a virtual network.


