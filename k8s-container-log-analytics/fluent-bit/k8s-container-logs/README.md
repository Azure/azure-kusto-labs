# 1.0. About
This is a scripted lab (all instructions provided) that details how to integrate Kubernetes container logs into Azure Data Explorer as a straight-through process for log analytics.  This lab is meant to be instructional.  We recommend leveraging our state o the art and turnkey offering from Azure for container log analytics - [Azure monitor with container insights](https://docs.microsoft.com/en-us/azure/azure-monitor/insights/container-insights-overview).  

# 2.0. Setup
Its important that you have your environment created exactly as detailed in the [landing page](../README.md) for this lab.

# 3.0. Details/background

#### 3.0.1. Kubernetes container logs location
All logs are available on the nodes at /var/log/conatiners*

#### 3.0.2. Ingestion pipeline
We will leverage Fluent Bit to tail logs (tail input plugin) in /var/log/containers/* and forward the log to Azure Event Hub (Kafka head) with the Kafka output plugin of Event Hub

24-fb-pipeline.png


# 4.0. Lab






