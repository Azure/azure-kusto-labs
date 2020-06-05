##### KAFKA INTEGRATION LABS

[Distributed Kafka ingestion with Confluent Platform](README.md)
<hr>

# 1. FOCUS: CREATE ADX TABLE & GRANTS
This document details creation of an ADX table and grants to write to the name, to the service principal we created earlier.<br>

```
// Drop table if exists
.drop table crimes_curated_kafka_confluent ifexists 

```


```
// Create table
.create table ['crimes_curated_kafka_confluent']  (['case_id']:int, ['case_nbr']:string, ['case_dt_tm']:datetime, ['block']:string, ['iucr']:string, ['primary_type']:string, ['description']:string, ['location_description']:string, ['arrest_made']:bool, ['was_domestic']:bool, ['beat']:string, ['district']:string, ['ward']:int, ['community_area']:int, ['fbi_code']:string, ['x_coordinate']:int, ['y_coordinate']:int, ['case_year']:int, ['updated_dt']:datetime, ['latitude']:real, ['longitude']:real, ['location_coords']:string, ['case_timestamp']:datetime, ['case_month']:int, ['case_day_of_month']:int, ['case_hour']:int, ['case_day_of_week_nbr']:int, ['case_day_of_week_name']:string)
```

```
// Create mapping
.create table ['crimes_curated_kafka_confluent'] ingestion json mapping 'crimes_curated_kafka_confluent_mapping' '[{"column":"case_id","path":"$.case_id","datatype":"int"}, {"column":"case_nbr","path":"$.case_nbr","datatype":"string"}, {"column":"case_dt_tm","path":"$.case_dt_tm","datatype":"datetime"}, {"column":"block","path":"$.block","datatype":"string"}, {"column":"iucr","path":"$.iucr","datatype":"string"}, {"column":"primary_type","path":"$.primary_type","datatype":"string"}, {"column":"description","path":"$.description","datatype":"string"}, {"column":"location_description","path":"$.location_description","datatype":"string"}, {"column":"arrest_made","path":"$.arrest_made","datatype":"bool"}, {"column":"was_domestic","path":"$.was_domestic","datatype":"bool"}, {"column":"beat","path":"$.beat","datatype":"string"}, {"column":"district","path":"$.district","datatype":"string"}, {"column":"ward","path":"$.ward","datatype":"int"}, {"column":"community_area","path":"$.community_area","datatype":"int"}, {"column":"fbi_code","path":"$.fbi_code","datatype":"string"}, {"column":"x_coordinate","path":"$.x_coordinate","datatype":"int"}, {"column":"y_coordinate","path":"$.y_coordinate","datatype":"int"}, {"column":"case_year","path":"$.case_year","datatype":"int"}, {"column":"updated_dt","path":"$.updated_dt","datatype":"datetime"}, {"column":"latitude","path":"$.latitude","datatype":"real"}, {"column":"longitude","path":"$.longitude","datatype":"real"}, {"column":"location_coords","path":"$.location_coords","datatype":"string"}, {"column":"case_timestamp","path":"$.case_timestamp","datatype":"datetime"}, {"column":"case_month","path":"$.case_month","datatype":"int"}, {"column":"case_day_of_month","path":"$.case_day_of_month","datatype":"int"}, {"column":"case_hour","path":"$.case_hour","datatype":"int"}, {"column":"case_day_of_week_nbr","path":"$.case_day_of_week_nbr","datatype":"int"}, {"column":"case_day_of_week_name","path":"$.case_day_of_week_name","datatype":"string"}]'
```

```
// Batching policy override of defaults, to consume faster
.alter table crimes_curated_kafka_confluent policy ingestionbatching @'{"MaximumBatchingTimeSpan":"00:00:05", "MaximumNumberOfItems": 20, "MaximumRawDataSizeMB": 300}'
```

```
// Grant SPN access to database
.add database crimes_db admins  ('aadapp=<yourServicePrincipalAppId>;<yourAADTenantID>') 'AAD App'
```

This concludes this module.<br>

<hr>

[Distributed Kafka ingestion with Confluent Platform](README.md)

