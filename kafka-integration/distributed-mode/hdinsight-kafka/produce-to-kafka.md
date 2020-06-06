##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with HDInsight Kafka](README.md)
<hr>

# 1. FOCUS: UPDATE BROKER DETAILS IN SPARK NOTEBOOK, and push events to Kafka
This document details broker conf update in the Databricks Spark notebook, and producing to Kafka from Spark.<br>

# 2. Update the broker IP list in your Spark notebook and run the notebook

1.  Navigate to your resource group, launch the Databricks workspace and start your Databricks cluster.
2.  Open the notebok called "1-kafka-hdi-producer-batch" and update the broker conf to the CSV you created [here](create-hdi.md#29-capture-kafka-broker-ips-and-kafka-zookeeper-ips-from-ambari---hosts-page).


![ADB-10](../images/ADB-12.png)
<br>
<hr>

# 3. Go to Confluent Control Center web UI and check if the messages published made  it


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

[Distributed Kafka ingestion with HDInsight Kafka](README.md)
