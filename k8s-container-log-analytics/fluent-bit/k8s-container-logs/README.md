# 1.0. About
This is a scripted lab (all instructions provided) that details how to integrate Kubernetes container logs into Azure Data Explorer as a straight-through process for log analytics.

# 2.0. Setup
Its important that you have your environment created exactly as detailed in the [landing page](../README.md) for this lab.

# 3.0. Where are the Kubernetes container logs available
The following is what your cluster would look like when you deploy apps as pods with 1..many containers.
All logs are available on the nodes at /var/log/conatiners*

# 4.0. How do we ingest into Azure Data Explorer?
We will leverage Fluent Bit to tail logs (tail input plugin) in /var/log/containers/* and forward the log to Azure Event Hub (Kafka head) with the Kafka output plugin of Event Hub

# 5.0. What does the log pipeline look like?

# 6.0. Does Fluent Bit create pods as well?  
Yes, it does, and it creates one for each node.

# 7.0. Lab






