##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with Confluent Platform](README.md)
<hr>

# 1. FOCUS: UPDATE BROKER DETAILS IN SPARK NOTEBOOK
This document details broker conf update in the Databricks Spark notebook, and producing to Kafka from Spark.<br>

# 2. Update the broker load balancer private IP in your Spark notebook and run the notebook

1.  Navigate to your resource group, launch the Databricks workspace and start your Databricks cluster.
2.  Open the notebok called "2-kafka-confluent-producer-batch" and update the broker conf from this step, to reflect your loadbalancer private IP and click on "Run all"


![ADB-10](../images/ADB-10.png)
<br>
<hr>

![ADB-15](../images/ADB-15.png)
<br>
<hr>

![ADB-16](../images/ADB-16.png)
<br>
<hr>


This concludes our producer smoke testing.  In the next step, we will consume from Kafka and sink to ADX.


<br>
This concludes this module.

<hr>

[Distributed Kafka ingestion with Confluent Platform](README.md)
