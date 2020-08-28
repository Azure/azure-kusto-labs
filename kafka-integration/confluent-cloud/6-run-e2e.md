
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

This is the last module of the hands on lab.  In this module, we will publish messages from Spark to Kafka and watch it flow to ADX through the KafkaConnect integration pipeline.

![E2E](images/06-E2E-12.png)
<br>
<br>
<hr>
<br>

[1. Run the Kafka producer in Spark on Azure Databricks](6-run-e2e.md#1--run-the-kafka-producer-in-spark-on-azure-databricks)<br>
[2. Observe the Kafka data flow, topic, consumer groups, consumers and messages of the pipeline in the Confluent Cloud](6-run-e2e.md#2--observe-the-kafka-data-flow-topic-consumer-groups-consumers-and-messages-of-the-pipeline-in-the-confluent-cloud)<br>
[3. Switch to Azure Data Explorer web UI and validate data delivery](6-run-e2e.md#3-switch-to-azure-data-explorer-web-ui-and-validate-data-delivery)<br>

## 1.  Run the Kafka producer in Spark on Azure Databricks

Log on to the Databricks cluster, ensure the cluster is running, if not start it.  Navigate to the Kafka producer notebook and run it.

![E2E](images/06-E2E-01.png)
<br>
<br>
<hr>
<br>

## 2.  Observe the Kafka data flow, topic, consumer groups, consumers and messages of the pipeline in the Confluent Cloud

Log on to the Confluent cloud cluster.

### 2.1. Click on your cluster

![E2E](images/06-E2E-02.png)
<br>
<br>
<hr>
<br>

### 2.2. Click on Data Flow

![E2E](images/06-E2E-03.png)
<br>
<br>
<hr>
<br>

### 2.3. Review the Data Flow

![E2E](images/06-E2E-04.png)
<br>
<br>
<hr>
<br>

### 2.4. Click on consumer groups, then on the connect-* consumer group

![E2E](images/06-E2E-05.png)
<br>
<br>
<hr>
<br>

### 2.6. Review the consumers in the consumer group and their mapping to partitions
Each consumer is a connector task.

![E2E](images/06-E2E-06.png)
<br>
<br>
<hr>
<br>

### 2.7. Review the topics
Notice the three topics created by KafkaConnect and also our topic - "crimes".  Lets click on "crimes".


![E2E](images/06-E2E-07.png)
<br>
<br>
<hr>
<br>

### 2.8. The crimes topic - a pictorial view

Click on messages while here.

![E2E](images/06-E2E-08.png)
<br>
<br>
<hr>
<br>

### 2.9. Watch the live messages streaming in and displayed


![E2E](images/06-E2E-09.png)
<br>
<br>
<hr>
<br>

## 3. Switch to Azure Data Explorer web UI and validate data delivery
You should also see all messages consumed on Confluent Cloud.<br>

### 3.1. Run a count to ensure the data made it
Here is the Kusto query to check counts-
```
crimes | count
```

![E2E](images/06-E2E-10.png)
<br>
<br>
<hr>
<br>

### 3.2. Select a few records to make sure they parsed right

Here is the Kusto query to view a few records-
```
crimes | take 2
```

![E2E](images/06-E2E-13.png)
<br>
<br>
<hr>
<br>

<br><br><hr>
This concludes the lab.  Please be sure to delete the resource group you created.

#### Main menu
[Home page](README.md)<br>
[1. Provision foundational resources](1-foundational-resources.md)<br>
[2. Provision Confluent Cloud and configure Kafka](2-confluent-cloud.md)<br>
[3. Provision Azure Data Explorer, and associated database objects and permissions](3-adx.md)<br>
[4. Import the Spark Kafka producer code, and configure Spark to produce to your Confluent Cloud Kafka topic](4-configure-spark.md)<br>
[5. Configure the KafkaConnect cluster, launch connector tasks](5-configure-connector-cluster.md)<br>
[6. Run the end to end pipeline](6-run-e2e.md)<br>
<hr>






