# About

This module covers -
![Spark](images/Spark.png)
<br>
<br>
<hr>


[1.  Import Spark code from Github into your Databricks workspace]()<br>
[2.  Paste your storage and kafka configs into the notebook 0-configs]()<br>
[3.  Mount your Azure Storage Account containers to your Databricks workspace]()<br>
[4.  Download a public dataset and curate it for use in the lab]()<br>
[5.  Publish curated data as messages to Kafka from Spark on Databricks]()<br>

## 1.  Import Spark code from Github into your Databricks workspace
Log on to your Databricks workspace from module 1.  Launch workspace.  Follow the steps below to run through the process of importing the code.<br>
The Spark code is available here-<br>
https://github.com/Azure/azure-kusto-labs/blob/confluent-clound-hol/kafka-integration/confluent-cloud/dbc/confluent-cloud-adx-hol.dbc
<br>
You will need this link for importing.


## 2.  Paste your storage and kafka configs into the notebook 0-configs
This notebook will be called in the subsequent notebooks that need to reference the storage and kafka configs.

## 3.  Mount your Azure Storage Account containers to your Databricks workspace
This allows you to read/write from storage containers like they are local file systems.  Run the notebook using the "Run all" button at the top of the notebook.



## 4.  Download a public dataset and curate it for use in the lab
We will download Chicago crimes public dataset and curate it. Run the notebook using the "Run all" button at the top of the notebook.

## 5.  Read the Chicago crimes data in Spark and publish to Kafka as Json messabes

![Spark](images/04-producer-01.png)
<br>
<br>
<hr>
<br>

![Spark](images/04-producer-02.png)
<br>
<br>
<hr>
<br>

![Spark](images/04-producer-03.png)
<br>
<br>
<hr>
<br>




The following snippet shows how to publish to Kafka from Spark-
```
 producerDF.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)")
.write
.format("kafka")
.option("kafka.bootstrap.servers", kafkaBootstrapServers)
.option("topic", kafkaTopic)
.option("kafka.request.timeout.ms", "20000")
.option("kafka.retry.backoff.ms", "500")
.option("kafka.ssl.endpoint.identification.algorithm", "https")
.option("kafka.security.protocol","SASL_SSL") 
.option("kafka.sasl.mechanism", "PLAIN") 
.option("kafka.sasl.jaas.config", "kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required username=\"" + kafkaAPIKey + "\" password=\"" + kafkaAPISecret + "\";")
.save
```

<hr>
This concludes this module.  Click here for the next module.
