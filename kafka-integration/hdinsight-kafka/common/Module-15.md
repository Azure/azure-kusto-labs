

# About

This module covers publishing curated Chicago crimes to Kafka<br>


### 1. Update the topic name and broker list with your details
![CreateStorage01](images/04-databricks-46.png)
<br>
<hr>
<br>

### 2. Run the notebook
![CreateStorage02](images/04-databricks-47.png)
<br>
<hr>
<br>

### 3.  In 2.0.2, we are creating a dataframe containing the curated data
![CreateStorage03](images/04-databricks-48.png)
<br>
<hr>
<br>

### 4.  In 2.0.3, we are formatting the data to a Kafka compatible format in another dataframe
![CreateStorage03](images/04-databricks-49.png)
<br>
<hr>
<br>

### 5.  Here, we are just exploring the schema
![CreateStorage03](images/04-databricks-50.png)
<br>
<hr>
<br>

### 6.  A quick count in Spark SQL
![CreateStorage03](images/04-databricks-51.png)
<br>
<hr>
<br>

### 7.  Finally, publish the dataframe from #4, to Kafka
![CreateStorage03](images/04-databricks-52.png)
<br>
<hr>
<br>

This concludes the module.<br>
[Return to the menu](https://github.com/anagha-microsoft/adx-kafkaConnect-hol/tree/master/hdi-standalone-nonesp#lets-get-started)
