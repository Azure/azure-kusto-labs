# 1.0. About
This is a scripted lab (all instructions provided) that details how to integrate Kubernetes container logs into Azure Data Explorer as a straight-through process for log analytics.  This lab is meant to be instructional.  We recommend leveraging our state o the art and turnkey offering from Azure for container log analytics - [Azure monitor with container insights](https://docs.microsoft.com/en-us/azure/azure-monitor/insights/container-insights-overview).  

# 2.0. Setup
Its important that you have your environment created exactly as detailed in the [landing page](../README.md) for this lab.

# 3.0. Architecture and details

### 3.0.1. Kubernetes container logs location
All logs are available on the nodes at /var/log/conatiners*

### 3.0.2. Ingestion pipeline
We will leverage Fluent Bit to tail logs (tail input plugin) in /var/log/containers/* and forward the log to Azure Event Hub (Kafka head) with the Kafka output plugin of Event Hub

![FB](../images/24-fb-pipeline.png)

### 3.0.3. Fluent-Bit log collection and forwarding demystified

Fluent-bit log collection and forwarding as described pictorially above, is achieved by creating a namespace, and deploying fluent-bit as an application on the cluster.  It creates a pod per node.  In the input section of the Fluent-Bit config map, we need to supply the directory to tail (/var/log/containers/\*), parser to use (optional, the author has used docker parser provided by Fluent Bit) and an output plugin - we will use Kafka here.  Deploying the tds agent config launches fluent-bit in the pods and starts collection and forwarding.

# 4.0. Lab

### 4.0.1. Create an Azure Data Explorer table and json mapping

Navigate to your ADX cluster on the portal and click on your database


### 4.0.2. Create an Azure Data Explorer - Data Ingestion Connection

Navigate to your ADX cluster on the portal and click on your database.  In the author's example - logs_db.<br>
This opens up a UI that lists "Data Ingestion" on the left navigation bar.<br>
Select the same and set up a connection from the Azure Event hub topic - container-log-topic to the table from 






