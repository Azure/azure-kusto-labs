#### Main menu
[Home page](README.md)<br>
[1. Provision foundational resources](1-foundational-resources.md)<br>
[2. Provision Confluent Cloud and configure Kafka](2-confluent-cloud.md)<br>
[3. Provision Azure Data Explorer, and associated database objects and permissions](3-adx.md)<br>
[4. Import the Spark Kafka producer code, and configure Spark to produce to your Confluent Cloud Kafka topic](4-configure-spark.md)<br>
[5. Configure the KafkaConnect cluster, launch connector tasks](5-configure-connector-cluster.md)<br>
[6. Run the end to end pipeline](6-run-e2e.md)<br>
<hr>

# About this module

This module features provisioning of the following resources:<br>
![RG](images/Foundational-Resources.png)
<br>
<br>
<hr>
<br>

[1. An Azure Resource Group](1-foundational-resources.md#1-provision-an-azure-resource-group) <br>
[2. An Azure Storage Account](1-foundational-resources.md#2-provision-an-azure-storage-account) <br>
[3. An Azure Databricks Workspace and Cluster](1-foundational-resources.md#3-provision-an-databricks-workspace-and-cluster) <br>
[4. An Azure Kubernetes Service Cluster](1-foundational-resources.md#4-provision-an-azure-kubernetes-service-cluster) <br>
[5. An Azure Active Directory Service Principal](https://github.com/Azure/azure-kusto-labs/blob/confluent-clound-hol/kafka-integration/confluent-cloud/1-foundational-resources.md#5-provision-an-azure-active-directory-service-principal)<br>

## 1. Provision an Azure Resource Group

An Azure resource group is a logical container for your Azure resources for the lab.  Follow the steps below to provision an Azure resource group<br>

![RG](images/01-rg-01.png)
<br>
<br>
<hr>
<br>

![RG](images/01-rg-02.png)
<br>
<br>
<hr>
<br>

![RG](images/01-rg-03.png)
<br>
<br>
<hr>
<br>

![RG](images/01-rg-04.png)
<br>
<br>
<hr>
<br>

![RG](images/01-rg-05.png)
<br>
<br>
<hr>
<br>



## 2. Provision an Azure Storage Account

We will need an Azure storage account to download a public dataset, and transform it for use in the lab.  We will need three storage containers, one for downloading, one for raw data and one for curated data.  Follow the screenshots below to provision the storage account and containers.

### Provision the account

![STORAGE](images/01-storage-01.png)
<br>
<br>
<hr>
<br>

![STORAGE](images/01-storage-02.png)
<br>
<br>
<hr>
<br>

![STORAGE](images/01-storage-03.png)
<br>
<br>
<hr>
<br>

![STORAGE](images/01-storage-04.png)
<br>
<br>
<hr>
<br>

![STORAGE](images/01-storage-05.png)
<br>
<br>
<hr>
<br>

![STORAGE](images/01-storage-06.png)
<br>
<br>
<hr>
<br>

![STORAGE](images/01-storage-07.png)
<br>
<br>
<hr>
<br>

![STORAGE](images/01-storage-08.png)
<br>
<br>
<hr>
<br>

### Provision storage containers

![STORAGE](images/01-storage-09.png)
<br>
<br>
<hr>
<br>

![STORAGE](images/01-storage-10.png)
<br>
<br>
<hr>
<br>

![STORAGE](images/01-storage-11.png)
<br>
<br>
<hr>
<br>

![STORAGE](images/01-storage-15.png)
<br>
<br>
<hr>
<br>

### Capture storage account key for use in the lab

![STORAGE](images/01-storage-13.png)
<br>
<br>
<hr>
<br>

![STORAGE](images/01-storage-14.png)
<br>
<br>
<hr>
<br>


## 3. Provision an Databricks Workspace and Cluster
We will use Spark on Azure Databricks to produce to Kafka some data.  Follow the steps below to provision an Azure Databricks workspace and cluster.

### Provision an Azure Databricks workspace

![SPARK](images/01-spark-01.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-02.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-03.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-04.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-05.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-06.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-07.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-08.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-09.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-10.png)
<br>
<br>
<hr>
<br>


### Create a Spark cluster

![SPARK](images/01-spark-11.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-12.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-13.png)
<br>
<br>
<hr>
<br>

![SPARK](images/01-spark-14.png)
<br>
<br>
<hr>
<br>


## 4. Provision an Azure Kubernetes Service Cluster

We will run the Kafka connectors on an Azure Kubernetes Service (AKS) instance.  This section covers creartion of an AKS cluster.

![K8S](images/01-aks-01.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-02.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-03.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-04.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-05.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-06.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-07.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-08.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-09.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-10.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-11.png)
<br>
<br>
<hr>
<br>


![K8S](images/01-aks-12.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-13.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-14.png)
<br>
<br>
<hr>
<br>

![K8S](images/01-aks-15.png)
<br>
<br>
<hr>
<br>


![K8S](images/01-aks-16.png)
<br>
<br>
<hr>
<br>



## 5. Provision an Azure Active Directory Service Principal
We will use an Azure Active Directory Service Principal as the privileged identity with access to ADX tables for accessing ADX from Kafka connectors.<br>
There are three items we need to save for subsequent use in this lab-<br>
1.  Azure Active Directory Service Principal Name (SPN) client ID<br>
2.  Azure Active Directory Service Principal Name (SPN) secret<br>
3.  Azure Active Directory Service tenant ID<br>
Ensure you write them down some place...<br><br>

The following are steps to create the same- <br>

![SPN](images/01-spn-01.png)
<br>
<br>
<hr>
<br>

![SPN](images/01-spn-02.png)
<br>
<br>
<hr>
<br>

![SPN](images/01-spn-03.png)
<br>
<br>
<hr>
<br>

![SPN](images/01-spn-04.png)
<br>
<br>
<hr>
<br>

![SPN](images/01-spn-05.png)
<br>
<br>
<hr>
<br>

![SPN](images/01-spn-08.png)
<br>
<br>
<hr>
<br>

![SPN](images/01-spn-07.png)
<br>
<br>
<hr>
<br>

![SPN](images/01-spn-08.png)
<br>
<br>
<hr>
<br>

![SPN](images/01-spn-09.png)
<br>
<br>
<hr>
<br>

![SPN](images/01-spn-10.png)
<br>
<br>
<hr>
<br>

# 6.  Jot down the information you need for the lab

| # | Key | Value |
| :--- | :--- | :--- |
| 1 | Resource group| kafka-confluentcloud-lab-rg |
| 2 | Azure region|  |
| 3 | Azure storage account|  |
| 4 | Azure storage account key|  |
| 5 | Azure Active Directory Service Principal application/client ID|  |
| 6 | Azure Active Directory Service Principal application secret key|  |
| 7 | Azure Active Directory tenant ID|  |

<hr>

This concludes this module.  Click [here](2-confluent-cloud.md) to proceed to the next module.

<hr>

#### Main menu
[Home page](README.md)<br>
[1. Provision foundational resources](1-foundational-resources.md)<br>
[2. Provision Confluent Cloud and configure Kafka](2-confluent-cloud.md)<br>
[3. Provision Azure Data Explorer, and associated database objects and permissions](3-adx.md)<br>
[4. Import the Spark Kafka producer code, and configure Spark to produce to your Confluent Cloud Kafka topic](4-configure-spark.md)<br>
[5. Configure the KafkaConnect cluster, launch connector tasks](5-configure-connector-cluster.md)<br>
[6. Run the end to end pipeline](6-run-e2e.md)<br>
<hr>

