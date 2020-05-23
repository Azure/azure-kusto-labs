

# About

This module covers provisioning an Azure Active Directory (AAD) Service Principal (SPN).  We will grant this SPN, the "ingestor" role in ADX, in the next module, and leverage the same to sink to ADX from Kafka in the KafkaConnect module.<br>

Navigate to portal.azure.com on your browser and follow the steps below:<br>

### 1. Click on Azure Active Directory
![CreateStorage01](images/01-spn-01.png)
<br>
<hr>
<br>

### 2. Click on App Registrations
![CreateStorage02](images/01-spn-02.png)
<br>
<hr>
<br>

### 3. Click on New Registration
![CreateStorage03](images/01-spn-03.png)
<br>
<hr>
<br>


### 4. Enter details as described
![CreateStorage05](images/01-spn-04.png)
<br>
<hr>
<br>

### 5. A service principal name/SPN gets created.  Make a note of the application/client ID and tenant ID; We will need this in the KafkaConnect module
![CreateStorage06](images/01-spn-05.png)
<br>
<hr>
<br>

### 6. Click on certificates and secrets; We will create a secret for the SPN
![CreateStorage07](images/01-spn-06.png)
<br>
<hr>
<br>

### 7. Click on new secret
![CreateStorage08](images/01-spn-07.png)
<br>
<hr>
<br>

### 8. Enter details and "add"
![CreateStorage09](images/01-spn-08.png)
<br>
<hr>
<br>

### 9. Make a note of the secret, it wont be available after.  We will need this in the KafkaConnect module
![CreateStorage10](images/01-spn-09.png)
<br>
<hr>
<br>


This concludes the module.<br>
[Return to the menu](README.md)
