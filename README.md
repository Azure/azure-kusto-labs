## About

<!-- 
Guidelines on README format: https://review.docs.microsoft.com/help/onboard/admin/samples/concepts/readme-template?branch=master

Guidance on onboarding samples to docs.microsoft.com/samples: https://review.docs.microsoft.com/help/onboard/admin/samples/process/onboarding?branch=master

Taxonomies for products and languages: https://review.docs.microsoft.com/new-hope/information-architecture/metadata/taxonomies?branch=master
-->

This repository features self-contained, hands-on-labs with detailed and step-by-step instructions, associated collateral (data, code etc) on trying out various features and integration points of Azure Data Explorer (Kusto)

## Labs

### 1.  Kafka Ingestion series
[Mutiple labs](https://github.com/Azure/azure-kusto-labs/tree/master/kafka-integration) that cover stan-alone and distributed modes of Kafka ingestion across Azure HDInsight and Confluent Kafka cluster flavors.

### 2.  Kubernetes Container Log Analytics
#### [2.1. Kubernetes Container Log Analytics with Fluent-Bit](k8s-container-log-analytics/fluent-bit/README.md)
Featuring Fluent-Bit v1.3.11 for log collection and forwarding, Azure Event Hub as streaming source, and straight through ingestion into Azure Data Explorer with our Azure Event Hub integration.<br>

### 3. Cosmos DB integration with Azure Data Explorer
#### [3.1 Cosmos DB integration with Azure Data Explorer using change feed](cosmosdb-adx-integration)
This lab covers end to end integration of Cosmos DB with Azure Data Explorer using Cosmos DB change feed for building near real-time analytical solution with a flavor of Azure Data Explorer dashboards.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
