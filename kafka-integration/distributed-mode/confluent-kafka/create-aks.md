##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with Confluent Platform](../README.md)
<hr>

# 1. FOCUS: AKS CLUSTER FOR KAFKA, KAFKACONNECT
This module covers creation of an Azure Kubernetes Service cluster that will serve as the infrastructure for Kafka and the KafkaConnect cluster running the ADX Kafka connector plugin.

# 2. Pre-requisites
You should have created all the foundational resources detailed in the docs [here.](../common/README.md)  This includes the subnet for Confluent.

# 3. Provision AKS

Create an AKS cluster in a Vnet with 9 nodes<br>
Standard D4s v3 (4 vcpus, 16 GiB memory)<br>
We will run 3 brokes, 1 or a node; 3 zookeepers, one on each node; 6 connectors, 2 on each node of the remaining 3 nodes<br>

![AKS-01](../images/confluent-01.png)
<br>
<hr>

![AKS-02](../images/confluent-02.png)
<br>
<hr>

![AKS-03](../images/confluent-03.png)
<br>
<hr>

In this step, you will need the service principal App ID and Secret that you created in [this step.](../common/create-spn.md) 
![AKS-04](../images/confluent-04.png)
<br>
<hr>

![AKS-05](../images/confluent-05.png)
<br>
<hr>

![AKS-06](../images/confluent-06.png)
<br>
<hr>

![AKS-07](../images/confluent-07.png)
<br>
<hr>

![AKS-08](../images/confluent-08.png)
<br>
<hr>

![AKS-09](../images/confluent-09.png)
<br>
<hr>

![AKS-10](../images/confluent-10.png)
<br>
<hr>

![AKS-11](../images/confluent-11.png)
<br>
<hr>

![AKS-12](../images/confluent-12.png)
<br>
<hr>

![AKS-20](../images/confluent-20.png)
<br>
<hr>

# 3. Associate the AKS auto-provisioned NSG with the Confluent subnet

If you search your resource groups, you will find that AKS created a new resource group and persisted some resources there.  One of these is an NSG.  We will associate this with the Confluent subnet.  This NSG gets automatically updated by Confluent operator, so this step is crucial for networking to work correctly.

![AKS-13](../images/confluent-13.png)
<br>
<hr>

![AKS-14](../images/confluent-14.png)
<br>
<hr>

![AKS-15](../images/confluent-15.png)
<br>
<hr>

![AKS-16](../images/confluent-16.png)
<br>
<hr>

![AKS-17](../images/confluent-17.png)
<br>
<hr>

![AKS-18](../images/confluent-18.png)
<br>
<hr>

![AKS-19](../images/confluent-19.png)
<br>
<hr>

This concludes this provisioning module.

[Distributed Kafka ingestion with Confluent Platform](../README.md)
<hr>


