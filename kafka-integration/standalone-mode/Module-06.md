
[Return to the HDI Kafka with standalone KafkaConnect menu](README.md) | [Kafka Integration Main Menu](../../README.md) <hr>

# About

This module covers provisioning a HDInsight cluster.  Navigate to your resource group, and click on "Add" and follow the steps below.<br>

### 1. Search for "Azure HDInsight"
![CreateHDI01](images/02-hdi-01.png)
<br>
<hr>
<br>

### 2. Click create
![CreateHDI02](images/02-hdi-02.png)
<br>
<hr>
<br>

### 3. Enter details, click on cluster type, select Kafka
![CreateHDI03](images/02-hdi-02a.png)
<br>
<hr>
<br>

### 4. Enter credentials
![CreateHDI04](images/02-hdi-02b.png)
<br>
<hr>
<br>

### 5. Select "new" storage
![CreateHDI05](images/02-hdi-03.png)
<br>
<hr>
<br>

### 6. Enter details as depicted
![CreateHDI05](images/02-hdi-04.png)
<br>
<hr>
<br>



### 7. Select TLS 1.2 in the networking tab 
![CreateHDI05](images/02-hdi-05.png)
<br>
<hr>
<br>

### 8. Select virtual network and kafka subnet 
![CreateHDI06](images/02-hdi-06.png)
<br>
<hr>
<br>

### 9. Leave default, except have 3 broker/worker nodes
![CreateHDI07](images/02-hdi-07.png)
<br>
<hr>
<br>

### 10. Click create
![CreateHDI08](images/02-hdi-08.png)
<br>
<hr>
<br>

### 11. You should see this icon for HDInsight in your resource group, click on it 
![CreateHDI09](images/02-hdi-09.png)
<br>
<hr>
<br>

### 12. In this UI, click on cluster dashboards
![CreateHDI10](images/02-hdi-10.png)
<br>
<hr>
<br>

### 13. Click on Ambari home; Ambari is the cluster manager
![CreateHDI11](images/02-hdi-11.png)
<br>
<hr>
<br>

### 14. Enter credentials
![CreateHDI12](images/02-hdi-12.png)
<br>
<hr>
<br>

### 15. You should see the cluster healthy
![CreateHDI13](images/02-hdi-13.png)
<br>
<hr>
<br>

### 16. Click on hosts
![CreateHDI14](images/02-hdi-14.png)
<br>
<hr>
<br>

### 17. Make a note of broker IPs with port number of 9092
E.g. for the below, its 10.15.1.12:9092,10.15.1.15:9092,10.15.1.18:9092

![CreateHDI15](images/02-hdi-15.png)
<br>
<hr>
<br>

### 18. Click on Kafka
![CreateHDI16](images/02-hdi-16.png)
<br>
<hr>
<br>

### 19. Click on configs
![CreateHDI17](images/02-hdi-17.png)
<br>
<hr>
<br>

### 20. In the search, type "Kafka-env"

![CreateHDI018](images/02-hdi-18.png)
<br>
<hr>
<br>

### 21. Paste this after the very last line for kafka-env

```
# Configure Kafka to advertise IP addresses instead of FQDN
IP_ADDRESS=$(hostname -i)
echo advertised.listeners=$IP_ADDRESS
sed -i.bak -e '/advertised/{/advertised@/!d;}' /usr/hdp/current/kafka-broker/conf/server.properties
echo "advertised.listeners=PLAINTEXT://$IP_ADDRESS:9092" >> /usr/hdp/current/kafka-broker/conf/server.properties

```

![CreateHDI19](images/02-hdi-19.png)
<br>
<hr>
<br>

### 22. Click on save
![CreateHDI20](images/02-hdi-20.png)
<br>
<hr>
<br>

### 23. Click on ok
![CreateHDI21](images/02-hdi-21.png)
<br>
<hr>
<br>

### 24. Lets go back to configs and search for "listener"
![CreateHDI22](images/02-hdi-22.png)
<br>
<hr>
<br>

### 25. Replace the value there with ```PLAINTEXT://0.0.0.0:9092.```
![CreateHDI23](images/02-hdi-23.png)
<br>
<hr>
<br>

### 26. Click on save
![CreateHDI24](images/02-hdi-24.png)
<br>
<hr>
<br>

### 27. Click on ok
![CreateHDI25](images/02-hdi-25.png)
<br>
<hr>
<br>

### 28. Click on restart to restart cluster after the conf changes
![CreateHDI26](images/02-hdi-26.png)
<br>
<hr>
<br>

### 29. You should see the restart
![CreateHDI27](images/02-hdi-27.png)
<br>
<hr>
<br>

### 30. And the cluster looking healthy
![CreateHDI28](images/02-hdi-28.png)
<br>
<hr>
<br>



This concludes the module.<br>

[Return to the HDI Kafka with standalone KafkaConnect menu](README.md) | [Kafka Integration Main Menu](../../README.md) <hr>
