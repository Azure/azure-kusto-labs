# About

This module covers provisioning Azure Data Explorer (ADX), creation of a database, table, table mapping and grants for the service principal we created to access the environment from the Kafka connector cluster.  We also configure an ingestion batching policy on the ADX table.  Our integration from Kafka to ADX is batch and queued.  So the tuning parameters of lowest of flush interval, flush bytes, flush items will trigger an ingestion into ADX and is conifgured via the ingestion batching policy.  We will execute the database object creations via the ADX web UI.

## 1. Provision an ADX cluster

Go to the portal, to your resource group, and click on 'Add' and type 'Azure Data Explorer' and run through the process of provisioning as detailed below. It is crucial to provision it in the same region as the rest of your Azure resources for the lab.  The author is using East US 2 as the region.

![CC](images/03-adx-01.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-02.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-03.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-04.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-05.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-06.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-07.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-08.png)
<br>
<br>
<hr>
<br>


![CC](images/03-adx-09.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-10.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-11.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-12.png)
<br>
<br>
<hr>
<br>

### Note down the cluster ingest URI - this is needed for Kafka ingestion.

![CC](images/03-adx-17.png)
<br>
<br>
<hr>
<br>


## 2. Create a database in your ADX cluster

![CC](images/03-adx-13.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-14.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-15.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-16.png)
<br>
<br>
<hr>
<br>

## 3. Launch the ADX Web UI

Follow the steps below to launch the ADX web UI of your cluster.

![CC](images/03-adx-18.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-18.png)
<br>
<br>
<hr>
<br>

![CC](images/03-adx-20.png)
<br>
<br>
<hr>
<br>


## 4. Create a table

```
// Drop table if exists
.drop table crimes ifexists

// Create table
.create table ['crimes']  (['case_id']:int,['case_nbr']:string, ['case_dt_tm']:string, ['block']:string,  ['iucr']:string, ['primary_type']:string, ['description']:string, ['location_description']:string, ['arrest_made']:bool, ['was_domestic']:bool,['beat']:string, ['district']:string, ['ward']:int, ['community_area']:int, ['fbi_code']:string, ['x_coordinate']:int, ['y_coordinate']:int, ['updated_dt']:datetime,['latitude']:real, ['longitude']:real, ['location_coords']:string, ['case_day_of_month']:int, ['case_hour']:int, ['case_day_of_week_nbr']:int, ['case_day_of_week_name']:string,['case_year']:int,   ['case_month']:int  )
```

## 5.  Create a table mapping
```
// Create mapping
.create table ['crimes'] ingestion avro mapping 'crimes_mapping' '[{"column":"case_id","path":"$.case_id"}, {"column":"case_nbr","path":"$.case_nbr"}, {"column":"case_dt_tm","path":"$.case_dt_tm"}, {"column":"block","path":"$.block"},  {"column":"iucr","path":"$.iucr"}, {"column":"primary_type","path":"$.primary_type"}, {"column":"description","path":"$.description"}, {"column":"location_description","path":"$.location_description"}, {"column":"arrest_made","path":"$.arrest_made"}, {"column":"was_domestic","path":"$.was_domestic"},{"column":"beat","path":"$.beat"}, {"column":"district","path":"$.district"}, {"column":"ward","path":"$.ward"}, {"column":"community_area","path":"$.community_area"}, {"column":"fbi_code","path":"$.fbi_code"}, {"column":"x_coordinate","path":"$.x_coordinate"}, {"column":"y_coordinate","path":"$.y_coordinate"},  {"column":"updated_dt","path":"$.updated_dt"}, {"column":"latitude","path":"$.latitude"}, {"column":"longitude","path":"$.longitude"}, {"column":"location_coords","path":"$.location_coords"},  {"column":"case_day_of_month","path":"$.case_day_of_month"}, {"column":"case_hour","path":"$.case_hour"}, {"column":"case_day_of_week_nbr","path":"$.case_day_of_week_nbr"}, {"column":"case_day_of_week_name","path":"$.case_day_of_week_name"},{"column":"case_year","path":"$.case_year"},{"column":"case_month","path":"$.case_month"}]'
```

## 6.  Configure the ADX batching policy
The ADX batching policy is a table level ingestion performance tuning knob for batch ingestion.

```
// Batching policy override of defaults, to consume faster
.alter table crimes policy ingestionbatching @'{"MaximumBatchingTimeSpan":"00:00:15", "MaximumNumberOfItems": 100, "MaximumRawDataSizeMB": 300}'
```

## 6.  Grant permission for your service principal to the database
```
// Grant SPN access to database
.add database crimes_db admins  ('aadapp=YourSPNAppID;YourTenantID') 'AAD App'
```

E.g.
```
.add database crimes_db admins  ('aadapp=4b59dd40-5302-abba-9f61-8d4923be3a64;72f988bf-doobiedoo-41af-91ab-2d7cd011db47') 'AAD App'
```

## 7.  Jot down the information you need for the lab

| # | Key | Value |
| :--- | :--- | :--- |
| 1 | Resource group| kafka-confluentcloud-lab-rg |
| 2 | Azure region|  |
| 3 | Azure storage account|  |
| 4 | Azure storage account key|  |
| 5 | Azure Active Directory Service Principal application/client ID|  |
| 6 | Azure Active Directory Service Principal application secret key|  |
| 7 | Azure Active Directory tenant ID|  |
| 8 | Kafka bootstrap server list|  |
| 9 | Kafka topic|  |
| 10 | Kafka API key|  |
| 11 | Kafka API secret|  |
| 12 | Kafka schema registry URL|  |
| 13 | ADX ingest cluster URL| <yourIngestClusterURI>|
| 14 | ADX database name| crimes_db|
| 14 | ADX table name| crimes|
| 14 | ADX table mapping name| crimes_mapping|
  
<br><br><hr>
This concludes this module.  You can now move to the [next module that covers configuring Spark - our Kafka producer.](https://github.com/Azure/azure-kusto-labs/blob/confluent-clound-hol/kafka-integration/confluent-cloud/4-configure-spark.md)
