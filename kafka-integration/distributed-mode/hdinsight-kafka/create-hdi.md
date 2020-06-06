##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with HDInsight](README.md)
<hr>


# 1. FOCUS: PROVISION HDINSIGHT KAFKA CLUSTER
This module covers creation of a HDInsight Kafka cluster and some configuration of the same.

# 2. Networking

## 2.1. Create a subnet for HDI in your Vnet

![HDI-00](../images/HDI-00.png)
<br><hr>

## 2.2. Create an NSG called zeus-hdi-nsg, with the following inbound rules

Include your IP address so you can connect to HDI.

![HDI-01](../images/HDI-01.png)
<br><hr>

## 2.3. Attach the NSG to the subnet

![HDI-02](../images/HDI-02.png)
<br><hr>

![HDI-03](../images/HDI-03.png)
<br><hr>

![HDI-04](../images/HDI-04.png)
<br><hr>

## 2.4. Provision HDInsight Kafka 4.0 (Kafka 2.1)
The diagram shows HDInsight 3.6, but provision HDInsight 4.0 instead.

![HDI-05](../images/HDI-05.png)
<br><hr>

![HDI-06](../images/HDI-06.png)
<br><hr>

![HDI-07](../images/HDI-07.png)
<br><hr>

![HDI-08](../images/HDI-08.png)
<br><hr>

![HDI-09](../images/HDI-09.png)
<br><hr>

![HDI-10](../images/HDI-10.png)
<br><hr>

![HDI-11](../images/HDI-11.png)
<br><hr>

![HDI-12](../images/HDI-12.png)
<br><hr>

![HDI-13](../images/HDI-13.png)
<br><hr>

![HDI-14](../images/HDI-14.png)
<br><hr>

![HDI-15](../images/HDI-15.png)
<br><hr>

## 2.5. Connect to Ambari to configure the cluster for use

![HDI-16](../images/HDI-16.png)
<br><hr>

![HDI-17](../images/HDI-17.png)
<br><hr>


![HDI-18](../images/HDI-18.png)
<br><hr>

## 2.5. Configure IP advertising in Ambari

Search for kafka-env in the Kafka configuration
![HDI-20](../images/HDI-20.png)
<br><hr>

Paste this at the end of the entry for kafka-env
```
# Configure Kafka to advertise IP addresses instead of FQDN
IP_ADDRESS=$(hostname -i)
echo advertised.listeners=$IP_ADDRESS
sed -i.bak -e '/advertised/{/advertised@/!d;}' /usr/hdp/current/kafka-broker/conf/server.properties
echo "advertised.listeners=PLAINTEXT://$IP_ADDRESS:9092" >> /usr/hdp/current/kafka-broker/conf/server.properties
```

Save the changes.

![HDI-21](../images/HDI-21.png)
<br><hr>

![HDI-22](../images/HDI-22.png)
<br><hr>

## 2.6. Configure listener & save  in Ambari

Search for listener in the Kafka configs and replace with -
```
PLAINTEXT://0.0.0.0:9092
```

![HDI-23](../images/HDI-23.png)
<br><hr>

![HDI-24](../images/HDI-24.png)
<br><hr>

![HDI-25](../images/HDI-25.png)
<br><hr>

![HDI-26](../images/HDI-26.png)
<br><hr>

## 2.7. Restart disks service in Ambari

Click on Kafka disks on the left navigation menu of Ambari and complete the steps below-

![HDI-27](../images/HDI-27.png)
<br><hr>

![HDI-28](../images/HDI-28.png)
<br><hr>

![HDI-30](../images/HDI-30.png)
<br><hr>

## 2.8. Restart Kafka brokers in Ambari

![HDI-31](../images/HDI-31.png)
<br><hr>

![HDI-32](../images/HDI-32.png)
<br><hr>

![HDI-33](../images/HDI-33.png)
<br><hr>

![HDI-34](../images/HDI-34.png)
<br><hr>

![HDI-35](../images/HDI-35.png)
<br><hr>

## 2.9. Capture Kafka broker IPs and Kafka zookeeper IPs from Ambari - Hosts page

![HDI-36](../images/HDI-36.png)
<br><hr>

Brokers with port CSV:
```
172.16.4.7:9092,172.16.4.5.98:9092,172.16.4.6:9092,172.16.4.4:9092
```

Zookeepers with port CSV:
```
172.16.4.10:2181,172.16.4.12:2181,172.16.4.14:2181
```


This concludes this module.<br>


<hr>

[Distributed Kafka ingestion with HDInsight](README.md)
