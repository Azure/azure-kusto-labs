
# KAFKA INTEGRATION LAB

[Common resources menu for distributed KafkaConnect mode for ingestion into ADX](README.md)
<hr>

# About

## Provisioning
- Details for provisioning a Vnet injected Databricks Spark cluster is available in Azure Databricks docs [here](https://docs.microsoft.com/en-us/azure/databricks/administration-guide/cloud-configurations/azure/vnet-inject).
- The author injected the cluster into zeus-vnet and specified two subnets - spark-priv-snet and spark-pub-snet that Databricks created.
- Databricks automatically created a network security group for the service, and associated it with the subnet.

## Code

A DBC that covers basic Kafka producer code, is [here]().  


## Import the DBC into your user home

As a best practice, import the DBC into your own user home, so you dont touch the original author's.

![Spark-1](../images/Spark-01.png)
<br>
<hr>

![Spark-2](../images/Spark-02.png)
<br>
<hr>

![Spark-3](../images/Spark-03.png)
<br>
<hr>

![Spark-4](../images/Spark-04.png)
<br>
<hr>


This concludes this provisioning and set up module.

[Common resources menu for distributed KafkaConnect](README.md)



