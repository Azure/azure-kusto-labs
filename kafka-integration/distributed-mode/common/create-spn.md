# KAFKA INTEGRATION LAB

[Common resources menu for distributed KafkaConnect mode for ingestion into ADX](README.md)
<hr>

# 1. About
This module covers provisioning an Azure Active Directory (AAD) Service Principal (SPN).  We will leverage this SPN to sink to ADX from Kafka.<br>  

Navigate to portal.azure.com on your browser and follow the steps below:<br>

### 1. Click on Azure Active Directory
![SPN-01](../images/01-spn-01.png)
<br>
<hr>
<br>

### 2. Click on App Registrations
![v02](../images/01-spn-02.png)
<br>
<hr>
<br>

### 3. Click on New Registration
![SPN-03](../images/01-spn-03.png)
<br>
<hr>
<br>


### 4. Enter details as described
![SPN-04v](../images/01-spn-04.png)
<br>
<hr>
<br>

### 5. A service principal name/SPN gets created.  Make a note of the application/client ID and tenant ID; We will need this in the KafkaConnect module
![SPN-05](../images/01-spn-05.png)
<br>
<hr>
<br>

### 6. Click on certificates and secrets; We will create a secret for the SPN
![SPN-06](../images/01-spn-06.png)
<br>
<hr>
<br>

### 7. Click on new secret
![SPN-07](../images/01-spn-07.png)
<br>
<hr>
<br>

### 8. Enter details and "add"
![SPN-08](../images/01-spn-08.png)
<br>
<hr>
<br>

### 9. Make a note of the secret, it wont be available after.  We will need this in the KafkaConnect module
![SPN-09](../images/01-spn-09.png)
<br>
<hr>
<br>

### 10.  You will need these three AAD related details in subsequent modules.  Make a note.

1.  AAD tenant ID
2.  AAD Service Principal application ID
3.  AAD Service Principal secret

This concludes the module.<br>

[Common resources menu for distributed KafkaConnect](README.md)
