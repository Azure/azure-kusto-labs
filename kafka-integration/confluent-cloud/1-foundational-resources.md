# About

This module features provisioning of the following resources:<br>
[1. An Azure Resource Group](1-foundational-resources.md#1-provision-an-azure-resource-group) <br>
[2. An Azure Storage Account](1-foundational-resources.md#2-provision-an-azure-storage-account) <br>
[3. An Azure Databricks Workspace and Cluster](1-foundational-resources.md#3-provision-an-databricks-workspace-and-cluster) <br>
[4. An Azure Kubernetes Service Cluster](1-foundational-resources.md#4-provision-an-azure-kubernetes-service-cluster) <br>
[5. Virtual Network peering configuration(1-foundational-resources.md#5-configure-virtual-network-peering) <br>
[6. An Azure Active Directory Service Principal]()<br>

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

## 5. Configure Virtual Network peering 
For the purpose of simplicity, we provisioned Azure Databricks and Azure Kubernetes Service standalone without creating a single virtual network with subnets for each service.  This ended up with each service creating its own virtual network. We need to locate these autocreated virtual networks and peer them to enable private communication between them.

### 5.1. Find the virtual network for your Kubernetes (Kafka connector) cluster 


![PEER](images/01-vnet-peer-01.png)
<br>
<br>
<hr>
<br>

![PEER](images/01-vnet-peer-02.png)
<br>
<br>
<hr>
<br>

![PEER](images/01-vnet-peer-03.png)
<br>
<br>
<hr>
<br>


### 5.2. Find the virtual network for your Databricks (Spark) cluster 

![PEER](images/01-vnet-peer-04.png)
<br>
<br>
<hr>
<br>

![PEER](images/01-vnet-peer-05.png)
<br>
<br>
<hr>
<br>

![PEER](images/01-vnet-peer-06.png)
<br>
<br>
<hr>
<br>


### 5.3. Peer #5.1 vnet with #5.2 vnet


## 6. Provision an Azure Active Directory Service Principal


