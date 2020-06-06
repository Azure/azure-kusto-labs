
##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with Confluent Platform](README.md)
<hr>

# 1. FOCUS: UPDATE ADX NSG
This document details updating ADX NSG to allow inbound from KafkaConnect cluster.<br>

# 2. Get the public IP addresses of the AKS cluster hosting Kafka

Locate the special resource group auto-created by AKS.<br>
Capture the public IPs.<br>

![NSG](../images/aks-nsg.png)
<br>
<hr>

# 3. Add the two IP addresses to the ADX NSG 

Create a bew inbound rule as shown below for your specific IPs.

![NSG](../images/adx-nsg.png)
<br>
<hr>

<hr>
This concludes the module.  The next one covers testing the integration.

 [Distributed Kafka ingestion with Confluent Platform](README.md)
