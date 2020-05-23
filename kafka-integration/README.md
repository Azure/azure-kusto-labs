# KAFKA INTEGRATION LABS
<br>

# About

This set of HoLs features Kafka integration with ADX and covers "how to integrate" with both the popluar Kafka offerings we see on Azure - **HDInsight Kafka** and **Confluent Kafka**.  <br>

## HDInsight Kafka
Is Azure's managed Kafka as a service with disaggregated compute and storage model and unlike other offerings of HDInsight, actually leverages managed disks with an option for you to choose a SKU with SSD/premium disks and also configure number of disks per node.<br><br>

## Confluent Kafka
Featured in the labs is a licensed (free for 30 days) version of Kafka from Confluent, runs on Azure Kubernetes Service (AKS), and leverages the Confluent operator for provisioning on AKS.<br><br>  

## KafkaConnect modes
Both **standalone** and **distributed** modes are covered, with distributed mode featuring Kusto connectors running on containers hosted on Azure Kubernetes Service.<br><br>  

## About the labs
The labs are end to end, scripted (no need to bing/google - not a hack) and self contained; They include provisioning the environment, starting services, downloading and generating data for the lab, publishing to Kafka, integrating into ADX; They come with detailed instructions, and include all commands for the lab.  

# Labs on HDInsight Kafka 3.6

| # | Focus |Environment | Details | Level |Time to complete |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | [Standalone KafkaConnect](standalone-edgenode/README.md) | KafkaConnect on HDInsight edge node | Self-contained, end to end, scripted lab to demonstrate by example how to integrate from HDI Kafka to ADX, with the KafkaConnect Kusto sink service.  Spark on Azure Databricks is leveraged to download the Chicago crimes dataset and publish to Kafka. | 300 | 4-8 hours|
