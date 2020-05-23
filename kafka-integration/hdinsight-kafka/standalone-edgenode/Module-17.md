

# About

This module covers validating the ingestion into Azure Data Explorer<br>

### 1. Double-check on the edge node to ensure that KafkaConnect service is running

![CreateStorage02](images/06-kck-18.png)
<br>
<hr>
<br>


### 2. On the Azure Data Explorer Web UI, run a count, a few times and you should see the number increasing

```
crimes_curated_kafka
| count
```

![CreateStorage01](images/06-kck-19.png)
<br>
<hr>
<br>

![CreateStorage01](images/06-kck-20.png)
<br>
<hr>
<br>

### 3. On the Azure Data Explorer Web UI, run a sample, to ensure data is parsed correctly
```
crimes_curated_kafka
| sample 10
```

![CreateStorage01](images/06-kck-21.png)
<br>
<hr>
<br>


This concludes the module.<br>
[Return to the menu](README.md)
