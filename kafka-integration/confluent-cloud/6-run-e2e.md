# About

In this module, we will publish data from Spark to Kafka and watch it flow through to ADX through the KafkaConnect integration pipeline.

## 1.  Run the Kafka producer in Spark on Azure Databricks

Log on to the Databricks cluster, ensure the cluster is running, if not start it.  Navigate to the Kafka producer notebook and run it.

![E2E](images/06-E2E-01.png)
<br>
<br>
<hr>
<br>

## 2.  Watch the Kafka part of the pipeline in the Confluent Cloud 

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
