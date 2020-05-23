# KAFKA INTEGRATION LABS
<br>

## With HDInsight 3.6 Kafka, and standalone KafkaConnect on an edge node

## 1. About
The focus of this hands-on-lab is to demonstrate how to configure KafkaConnect sink in a standalone mode, on Azure HDInsight Kafka PaaS, to sink to Azure Data Explorer (ADX).  The lab is fully "scripted" (its not a hack, no bing/googling required) - there are detailed, step by step, and comprehensive instructions and is intended to demonstrate the integration. It includes four distributed PaaS offerings - Azure storage v2, HDInsight Kafka and Azure Data Explorer, and Azure Databricks.
<br><br>
We will download the Chicago crimes public dataset for this exercise<br>
https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-present/ijzp-q8t2

**Out of scope:** This lab does not cover the more advanced topics of performance tuning, ADX in a VNet and distributed KafkaConnect.

## 2. Pre-requisites
- An Azure subscription with about $200 in funds
- About 8-10 hours of time
- Maybe some caffeine and some music
- Focus - there are a lot of steps, that need to be completed in sequential order and one step missed could be problematic for dependent steps
- Prior knowledge of Kafka, Spark, ADX and Azure, and the services in scope is not mandatory, but VERY helpful and may reduce the lab execution time to 2 hours

## 3. Solution pictorial overview
![Solution](images/solution-architecture.png)

<br>Our next iteration of this lab will include ADX in the Vnet as well

## What's covered in the lab

### Common:
1.  Provisioning an Azure resource group
2.  Provisioning a virtual network with subnets 
3.  Provisioning a storage account, and creating containers, and capturing storage account key for subsequent use
4.  Creating an Azure Active Directory (AAD) Service Principal (SPN), creating a secret, capturing tenant ID, SPN app ID, SPN secret for subsequent use

### Azure Data Explorer:
5.  Provisioning an ADX cluster
6.  Creating an ADX database, table and mapping reference
7.  Granting the AAD SPN, "ingestor" RBAC to the table 

### HDInsight Kafka:
8.  Provisioning a HDInsight Kafka cluster
8.  Provisioning an edge node on the Kafka cluster on which we will run KafkaConnect service
9.  Creating a Kafka topic in HDInsight
10. Configuring Kafka to broadcast IP addresses and configuring listener
11. Downloading KafkaConnect ADX sink jar on the edge node, copying it to the right location
12. Editing connect-standalone.properties with the broker:port list, and the plugin path to reflect the path the jar is located
13. Creating a kafka-connect-kusto.properties file with details about the sink (ADX conf)
14. Launching the KafkaConnect service

### Azure Databricks:
15. Provisioning an Azure Databricks cluster
16. Importing Spark scala code for the lab from git into your Databricks workspace
16. Mounting blob storage on the cluster
17. Downloading the Chicago crimes dataset to the raw information zone ("raw" container)
18. Curating the dataset (augmenting with temporal attributes and such) and persisting to the curated information zone ("curated" container)
19. Basic visualization in Spark (we will repeat this in Azure Data Explorer dashboard as well)
20. Read the Chicago crimes dataset from the curated information zone, and publish it to Kafka

### Azure Data Explorer:
21. Validate receipt of data from Kafka
22. Run some queries
23. Launch ADX dashboard and repeat #19

### Want a challenge?
24. Author a Spark notebook to publish the raw data to Kafka, and from there sink to a new ADX table defined for the raw data
25. Perform the transformations done in the Spark notebook in #18, in ADX
26. Create a new dashboard based off of the raw data that you curated in ADX

### Lets get started
[Module 1.  Provision a resource group](Module-01.md) <br>
[Module 2.  Provision a virtual network and subnets](Module-02.md) <br>
[Module 3.  Provision a storage account v2 and containers](Module-03.md) <br>
[Module 4.  Create an Azure Active Directory Service Principal and secret](Module-04.md) <br>
[Module 5.  Provision an Azure Data Explorer, create database objects and permissions ](Module-05.md) <br>
[Module 6.  Provision a HDInsight Kafka cluster](Module-06.md) <br>
[Module 7.  Provision an edge node on the HDInsight Kafka cluster](Module-07.md) <br>
[Module 8.  Create a Kafka topic on the Kafka cluster](Module-08.md) <br>
[Module 9.  Download and configure KafkaConnect on the edge node, launch the service](Module-09.md) <br>
[Module 10.  Provision a Databricks workspace](Module-10.md) <br>
[Module 11.  Create a Databricks cluster](Module-11.md) <br>
[Module 12.  Import the lab's Spark code into your Databricks workspace and review](Module-12.md) <br>
[Module 13.  Mount blob storage onto your Databricks workspace](Module-13.md) <br>
[Module 14.  Download and curate the Chicago crimes dataset](Module-14.md) <br>
[Module 15.  Stream the curated crimes dataset to Kafka](Module-15.md) <br>
[Module 16.  Validate the publishing with Kafka console consumer in HDInsight](Module-16.md) <br>
[Module 17.  Validate the ingestion in the ADX table](Module-17.md) <br>
[Module 18.  Run some analytics in ADX](Module-18.md) <br>
[Module 19.  Visualize with ADX dashboard](Module-19.md) <br>

### Got feedback?
If you have ideas on how we can improve this lab, and what else we can add to the lab series, connect with me (Anagha Khanolkar, Microsoft) on LinkedIn and message me.

