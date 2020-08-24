# 1. Hands-on-Lab: Azure Data Explorer integration with Kafka on Confluent Cloud managed PaaS

This lab details usage of self-managed Azure Data Explorer KafkaConnect sink connector with Confluent Cloud on Azure.<br>

## Pictorial overview of the lab

![RG](images/E2E.png)
<br>
<br>
<hr>
<br>

## 2.  Lab summary

The lab showcases very basic Kafka ingestion into ADX. It does not feature a real time usecase, and does not include some of the streaming capabilities of Confluent Cloud, and Kafka in general, to keep the lab simple and **Azure Data Explorer integration** focused.<br>

Essentially the following are the aspects covered in the lab; Each aspect covered includes provisioning (screenshots included), code, step-by-step instructions, commands and the outcome-<br>

### 2.1.  The data
We will use the Chicago crimes public dataset.  It is about 7 million records.<br>

### 2.2. Kafka on Azure
We will leverage Confluent Cloud on Azure

### 2.3. Kafka producer
We will use Spark on Databricks to publish to Kafka, as its a PaaS, easy to provision and use, for the simplicity of use of notebooks, and the distributed nature and the robust integration of Spark with Kafka.  

### 2.4. KafkaConnect cluster for integration
We will use Azure Kubernetes Service (AKS), collectively AKS and Kubernetes in general make a great platform for distributed KafkaConnect.

### 2.5. Azure Data Explorer cluster as the sink
For the purpose of simplicity, we will use a cluster that is not in a virtual network.

## 3. Other details

### 3.1. Audience for the lab

Any data practitioner - architect or developer.

### 3.2. Duration

Depends on your knowledge of Azure, and technologies included.  It should take about 8-12 hours if you are entirely unfamiliar.

### 3.3. Azure credit needed

Approximately $300-$600 - depends on familiarity worth services and Azure, and whether you work contiunously.

<hr>
Lets get started!
