# 1.0. About

This module covers creation of common resources across the two labs.

# 2.0. Create resource group
Create a resource group in a region of your choice.  Be sure to provision all resources for the labs into this one.<br>
https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/manage-resource-groups-portal#create-resource-groups


# 3.0. Create virtual network
Create a virtual network in the resource group, ensure you pick the same region as in #2.0.<br>
https://docs.microsoft.com/en-us/azure/virtual-network/quick-create-portal

# 4.0. Create subnets
Create subnets for the rest of the lab.<br>
![Subnets](../images/Subnets-Provision.png)
<br><hr>

# 5.0. Create an Azure Data Explorer (ADX) cluster

### 5.0.1. Create an NSG for ADX

Refer to the doc link below to determine what is the monitoring IP address for the Azure region you have chosen.<br>
We will need it to create an NSG inbound rule.<br>
https://docs.microsoft.com/en-us/azure/data-explorer/vnet-deployment#relevant-ip-addresses<br>

Create a network security group called adx-sng with these rules<br>
https://docs.microsoft.com/en-us/azure/virtual-network/manage-network-security-group#create-a-network-security-group<br>


![ADX-NSG](../images/adx-nsg.png)
<br><hr>

### 5.0.2. Create two public IP addresses for ADX's load balancers for the Data Management Service and Engine

https://docs.microsoft.com/en-us/azure/data-explorer/vnet-create-cluster-portal#create-public-ip-addresses

### 5.0.3. Associate the NSG with the ADX subnet
![ADX-NSG-2](../images/02-ADX.png)
<br><hr>

### 5.0.4. Provision Engine Public IP and DMS Public IP

Follow steps here...
https://docs.microsoft.com/en-us/azure/data-explorer/vnet-create-cluster-portal#create-public-ip-addresses

![ADX-NSG-4](../images/04-ADX.png)
<br><hr>

![ADX-NSG-5](../images/05-ADX.png)
<br><hr>

### 5.0.5. Provision Vnet injected cluster
Follow the instructions here.
https://docs.microsoft.com/en-us/azure/data-explorer/vnet-deployment

### 5.0.6. ADX cluster - URLs and database


The two URLS are important-

Ingest URL:
https://ingest-zeusadx.westeurope.kusto.windows.net

Web UI:
https://zeusadx.westeurope.kusto.windows.net

### 5.0.7. Create an ADX database in the cluster you created above


### 5.0.8. Launch the web UI and connect to the cluster

### 5.0.9. Create tables and permissions in the Web UI as shown below

# 5.0. Create an Azure Databricks Spark cluster

# 6.0. Import Spark code into the cluster





