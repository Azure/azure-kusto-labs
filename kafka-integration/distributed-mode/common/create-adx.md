# KAFKA INTEGRATION LAB

[Common resources menu for distributed KafkaConnect mode for ingestion into ADX](README.md)
<hr>

# 1. FOCUS: AZURE DATA EXPLORER CLUSTER
This module details creation of a Vnet injected ADX cluster.

# 2. Create an NSG for ADX
Navigate to the resource group you created on the portal.

Refer to the doc link below to determine what is the monitoring IP address for the Azure region you have chosen.<br>
We will need it to create an NSG inbound rule.<br>
https://docs.microsoft.com/en-us/azure/data-explorer/vnet-deployment#relevant-ip-addresses<br>

Create a network security group called adx-sng, in the right Azure region, with these rules<br>
https://docs.microsoft.com/en-us/azure/virtual-network/manage-network-security-group#create-a-network-security-group<br>


![ADX-NSG](../images/adx-nsg.png)
<br><hr>

# 3. Associate the NSG with the ADX subnet
![ADX-NSG-2](../images/02-ADX.png)
<br><hr>

# 4. Provision a Public IP for the engine and Public IP for the data management service

Follow steps here...<br>
https://docs.microsoft.com/en-us/azure/data-explorer/vnet-create-cluster-portal#create-public-ip-addresses

![ADX-NSG-4](../images/04-ADX.png)
<br><hr>

![ADX-NSG-5](../images/05-ADX.png)
<br><hr>

# 5. Provision a Vnet injected ADX cluster
Follow the instructions here.
https://docs.microsoft.com/en-us/azure/data-explorer/vnet-deployment

# 6. ADX cluster - URLs and database

![ADX-NSG-6](../images/06-ADX.png)
<br><hr>

The two URLS are important-

Ingest URL:
https://ingest-zeusadx.westeurope.kusto.windows.net

Web UI:
https://zeusadx.westeurope.kusto.windows.net

# 7. Create an ADX database in the cluster you created above

![ADX-NSG-7](../images/07-ADX.png)
<br><hr>

![ADX-NSG-8](../images/08-ADX.png)
<br><hr>

# 8. Launch the web UI and connect to the cluster

![ADX-NSG-9](../images/09-ADX.png)
<br><hr>


![ADX-NSG-10](../images/10-ADX.png)
<br><hr>

# 9. Create tables and permissions in the Web UI 

We will actually cover this separately under the individual lab modules for HDInsight and Confluent separately.

![ADX-NSG-11](../images/11-ADX.png)
<br><hr>

This concludes this provisioning and setup module.

[Common resources menu for distributed KafkaConnect](README.md)
