# About

This set of HoLs features Kafka integration of ADX - with **HDInsight Kafka**.  HDInsight is Azure's managed Kafka as a service with disaggregated compute and storage model and unlike other offerings of HDInsight, actually leverages managed disks with an option for you to choose a SKU with SSD/premium disks and also configure number of disks per node.

# Labs on HDInsight Kafka 3.6

| # | Focus |Environment | Details | Level |Time to complete |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Standalone KafkaConnect | KafkaConnect on HDInsight edge node | Self-contained, end to end, scripted lab to demonstrate by example how to integrate from HDI Kafka to ADX, with the KafkaConnect Kusto sink service.  Spark on Azure Databricks is leveraged to download the Chicago crimes dataset and publish to Kafka. | 300 | 4-8 hours|
