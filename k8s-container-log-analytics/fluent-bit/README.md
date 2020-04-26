# 1. About
Fluent Bit is an open source and multi-platform Log Processor and Forwarder which allows you to collect data/logs from different sources, unify and send them to multiple destinations. It's fully compatible with Docker and Kubernetes environments.

Fluent Bit is written in C, have a pluggable architecture supporting around 30 extensions. It's fast and lightweight and provide the required security for network operations through TLS.

For more information, visit https://fluentbit.io/

# 2. Hands-on-labs
Two hands on labs are featured that cover log collection, basic parsing, and forwarding with Fluent Bit from Kubernetes pods to Azure Data Explorer, ingestion into a structured format and some log analytics with Kusto Query Language.  Lab 1 covers Kubernetes logs, and lab 2 covers application logs.  

# 3. Pre-requisites
1.  An Azure subscription with about $100 in credit
2.  Basic knowledge of Azure services in scope
3.  Basics of Kubernetes

# 4. Lab environment

The lab environment consists of 4 Azure services in an Azure resource group, in a single region - similar to below.  A virtual network, an Azure Data Explorer cluster, an Azure Kubernets cluster and an Azure Event Hub namespace.

![Services](../../images/01-services.png)

### 4.1.  Azure resource provisioning
Choose an Azure region and provision all of the below in the same region, and into the resource group-
1.  Create an Azure resource group<br>
https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/manage-resource-groups-portal#create-resource-groups

2.  Create an Azure Data Explorer cluster in the resource group - basic SKU<br>
https://docs.microsoft.com/en-us/azure/data-explorer/create-cluster-database-portal

3.  Create an Azure Virtual Network in the resource group, with a subnet called app-snet<br>
https://docs.microsoft.com/en-us/azure/virtual-network/quick-create-portal#create-a-virtual-network<br>
Create only a virtual network, not the VMs

4.  Create an Azure Event Hub namespace in the resource group - standard SKU<br>
https://docs.microsoft.com/en-us/azure/event-hubs/event-hubs-create<br>
Do not create an event hub, just the event hub namespace.

5.  Create a shared access policy for the Azure Event Hub namespace and save the primary connection string for use in the lab <br>
https://docs.microsoft.com/en-us/azure/event-hubs/authenticate-shared-access-signature

6.  Create an Azure Kubernetes cluster, node size Standard_DS2_v2, with 3 nodes, in the subnet created in step 3 <br>
https://docs.microsoft.com/en-us/azure/aks/tutorial-kubernetes-deploy-cluster

### 4.2. CLI tools install
Install the following command line tools-

4.2.1.  Install Azure CLI <br>
https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest

4.2.2.  Login to Azure from your command line utility
```
az login
```
Authenticate yourself..

4.2.3.  Choose subscription in case you have multiple subscriptions
Replace "YOUR_SUBSCRIPTION_GUID" with your actual subscription guid
```
az account set --subscription YOUR_SUBSCRIPTION_GUID 
```

4.2.4.  Run the command below to check if you have AKS utils installed
```
kubectl version
```
If its not installed, run the below-
```
az aks install-cli
```
Re-run and check if you get the version-
```
kubectl version
```

4.2.5. Get access credentials for your managed Kubernetes cluster/AKS
```
az aks get-credentials --resource-group YOUR_RESOURCE_GROUP --name YOUR_AKS_NAME --admin
```
E.g.
az aks get-credentials --resource-group ankhanol4-rg --name veda-aks --admin

4.2.6. Check nodes
```
kubectl get nodes

# This is the author's output
NAME                                STATUS   ROLES   AGE    VERSION
aks-agentpool-11258432-vmss000000   Ready    agent   3d6h   v1.15.10
aks-agentpool-11258432-vmss000001   Ready    agent   3d6h   v1.15.10
aks-agentpool-11258432-vmss000002   Ready    agent   3d6h   v1.15.10
```

4.2.7. Check pods
```
kubectl get pods
```
This should return nothing

# 5. Labs

### 5.1.  Kubernetes container logs
This lab covers forwarding and processing of Kubernetes container logs - enriched with Kubernetes metadata. <br>
[Start the lab](k8s-container-logs/README.md)

### 5.2.  Application logs from containers
This lab covers forwarding and processing of (synthetic) app logs from within Kubernetes containers - strictly app logs and without Kubernetes metadata.

# Feedback
Please share any feedback you may have and also feel free to contribute. 
