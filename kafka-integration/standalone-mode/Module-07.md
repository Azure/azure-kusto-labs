# KAFKA INTEGRATION LABS
<br>

[Return to the HDI Kafka with standalone KafkaConnect menu](README.md) | [Kafka Integration Main Menu](../README.md) <hr>

# About

This module covers provisioning an edge node on an existing HDInsight cluster.  
Navigate to ythe URL https://docs.microsoft.com/en-us/azure/hdinsight/hdinsight-apps-use-edge-node

### 1. Click on deploy
![CreateHDI01](images/02-hdi-29.png)
<br>
<hr>
<br>

### 2. Enter details
![CreateHDI02](images/02-hdi-30.png)
<br>
<hr>
<br>

### 3. Agree to terms and click on purchase
![CreateHDI03](images/02-hdi-31.png)
<br>
<hr>
<br>

### 4. Monitor the provisioning to completion
![CreateHDI04](images/02-hdi-32.png)
<br>
<hr>
<br>

### 5. When it completes, it should look like this
![CreateHDI05](images/02-hdi-33.png)
<br>
<hr>
<br>

### 6. Switch back to Ambari, click on hosts
![CreateHDI05](images/02-hdi-34.png)
<br>
<hr>
<br>



### 7. Make a note of the edge node private IP address.  The edge node name starts with "e"
![CreateHDI05](images/02-hdi-35.png)
<br>
<hr>
<br>

### 8. On the left navigation panel, click on SSH, not cluster size 
![CreateHDI06](images/02-hdi-36.png)
<br>
<hr>
<br>

### 9. Copy the SSH command
![CreateHDI07](images/02-hdi-37.png)
<br>
<hr>
<br>

### 10. Using Putty or your Linux command line, or Azure cloud bash shell, SSH to the the cluster head node
![CreateHDI08](images/02-hdi-38.png)
<br>
<hr>
<br>

### 11. Enter your password
![CreateHDI09](images/02-hdi-39.png)
<br>
<hr>
<br>

### 12. Once logged in, SSH to the edge node with the IP you captured in the step 7; Use same password as SSH to head node 
![CreateHDI10](images/02-hdi-40.png)
<br>
<hr>
<br>

### 13. All is well if you are able to login
![CreateHDI11](images/02-hdi-41.png)
<br>
<hr>
<br>

This concludes the module.<br>

[Return to the HDI Kafka with standalone KafkaConnect menu](README.md) | [Kafka Integration Main Menu](../README.md) <hr>
