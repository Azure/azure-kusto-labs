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

### 3.0.3. Fluent-Bit log collection and forwarding - demystified

Fluent-bit log collection and forwarding as described pictorially above, is achieved by creating a namespace, and deploying fluent-bit as an application on the cluster.  It creates a pod per node.  In the input plugin section of the Fluent-Bit config map, we need to supply the directory to tail (/var/log/containers/\*), parser plugin to use (optional, the author has used docker parser provided by Fluent Bit) and an output plugin - we will use Kafka here (leverages librdkafka).  Deploying the tds agent config launches fluent-bit in the pods and starts collection and forwarding.

# 4.0. Lab

### 4.0.1. Create an Azure Data Explorer table and json mapping

#### 4.0.1.1. Launch the ADX Web UI
Navigate to your ADX cluster on the portal and launch the Azure Data Explorer web UI as follows:

![FB](../images/25-adx.png)

![FB](../images/26-adx.png)

![FB](../images/27-adx.png)

#### 4.0.1.2. Create a table for the container logs

Click on the database on the left navigation and then to the query editor and paste the script below and run it.

```
// Create table
.create table ['container_log_stream_stage']  (['_timestamp']:real, ['log']:string, ['stream']:string, ['time']:datetime, ['kubernetes_pod_name']:string, ['kubernetes_namespace_name']:string, ['kubernetes_pod_id']:guid, ['kubernetes_labels_component']:string, ['kubernetes_labels_controller-revision-hash']:string, ['kubernetes_labels_pod-template-generation']:int, ['kubernetes_labels_tier']:string, ['kubernetes_annotations_aks_microsoft_com_release-time']:string, ['kubernetes_host']:string, ['kubernetes_container_name']:string, ['kubernetes_docker_id']:string, ['kubernetes_container_hash']:string)

```

![FB](../images/28-adx.png)


#### 4.0.1.3. Create a mapping reference
Next create the mapping reference - this helps parse the incoming logs into the ADX table.

```
// Create mapping
.create table ['container_log_stream_stage'] ingestion json mapping 'container_log_stream_stage_mapping' '[{"column":"_timestamp","path":"$.@timestamp","datatype":"real"},{"column":"log","path":"$.log","datatype":"string"},{"column":"stream","path":"$.stream","datatype":"string"},{"column":"time","path":"$.time","datatype":"datetime"},{"column":"kubernetes_pod_name","path":"$.kubernetes.pod_name","datatype":"string"},{"column":"kubernetes_namespace_name","path":"$.kubernetes.namespace_name","datatype":"string"},{"column":"kubernetes_pod_id","path":"$.kubernetes.pod_id","datatype":"guid"},{"column":"kubernetes_labels_component","path":"$.kubernetes.labels.component","datatype":"string"},{"column":"kubernetes_labels_controller-revision-hash","path":"$.kubernetes.labels.controller-revision-hash","datatype":"string"},{"column":"kubernetes_labels_pod-template-generation","path":"$.kubernetes.labels.pod-template-generation","datatype":"int"},{"column":"kubernetes_labels_tier","path":"$.kubernetes.labels.tier","datatype":"string"},{"column":"kubernetes_annotations_aks_microsoft_com_release-time","path":"$.kubernetes.annotations.aks.microsoft.com/release-time","datatype":"string"},{"column":"kubernetes_host","path":"$.kubernetes.host","datatype":"string"},{"column":"kubernetes_container_name","path":"$.kubernetes.container_name","datatype":"string"},{"column":"kubernetes_docker_id","path":"$.kubernetes.docker_id","datatype":"string"},{"column":"kubernetes_container_hash","path":"$.kubernetes.container_hash","datatype":"string"}]'
```


### 4.0.2. Create an Azure Data Explorer - Data Ingestion Connection

Navigate to your ADX cluster on the portal and click on your database.  In the author's example - logs_db.<br>
This opens up a UI that lists "Data Ingestion" on the left navigation bar.<br>
Select the same and set up a connection from the Azure Event hub topic - container-log-topic to the table from 






