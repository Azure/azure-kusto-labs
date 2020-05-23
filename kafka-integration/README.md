# KAFKA INTEGRATION LABS
<br>

# About

This set of HoLs features Kafka integration with ADX.  The environments cover both the popluar ones we see on Azure - **HDInsight Kafka** and **Confluent Kafka**.  <br>

**HDInsight Kafka** is Azure's managed Kafka as a service with disaggregated compute and storage model and unlike other offerings of HDInsight, actually leverages managed disks with an option for you to choose a SKU with SSD/premium disks and also configure number of disks per node.<br><br>

**Confluent Kafka** featured  in #2 below, runs on Azure Kubernetes Service, and leverages the Confluent operator.<br><br>  

The labs are self contained, they include provisioning the environment, downloading and generating data for the lab, publishing to Kafka, integrating into ADX - are end to end, with detailed instructions, and include all commands for the lab.  

# Labs on HDInsight Kafka 3.6

| # | Focus |Environment | Details | Level |Time to complete |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | [Standalone KafkaConnect](standalone-edgenode/README.md) | KafkaConnect on HDInsight edge node | Self-contained, end to end, scripted lab to demonstrate by example how to integrate from HDI Kafka to ADX, with the KafkaConnect Kusto sink service.  Spark on Azure Databricks is leveraged to download the Chicago crimes dataset and publish to Kafka. | 300 | 4-8 hours|
