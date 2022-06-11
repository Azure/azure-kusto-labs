# Azure Data Explorer IoT Demo
If you are looking to explore the capabilities of Azure Data Explorer for IoT Analytics then you might need a sample environment to start with. Here we will walk you though an option of using Azure IoT Central to simulate thermastat IoT devices and send their telemetry data to Azure Data Explorer.

## Prerequesets
Azure Data Explorer Cluster with Database: the only thing you need provisioned ahead of time is a ADX cluster with a database that you will use to store the demo IoT telemetry.

## Step 1: Prepare the ADX Cluster
Before we jump over to IoT Central we need to prepare our ADX Cluster and Database:

### Create the tables
In this scenerio we are going to use two tables. One will be for ingesting the raw telemetry (StageIoTRawData) and the second table will be to flatten this structure using an update policy (Thermostat). This is a common scenerio where you want to do light transformations once the data lands in ADX.

1) In your Kusto Query tool of choice connect to your database and run the following two command:

```
.create table StageIoTRawData (deviceId: string, enqueuedTime: datetime, messageProperties: dynamic, messageSource: string, telemetry: dynamic) 
```
and 

```
.create table Thermostats (EnqueuedTimeUTC: datetime, DeviceId: string, BatteryLevel: long, Temp: real, Humidity: real) 
```

<img src="gif\IoTCreateTables.gif" width="740" />

2) Now we need to create the update policy for the Thermostat table. Before we create the policy we'll create a new function that it'll utilize. You can use the following command to create the function:

```
.create-or-alter function with (docstring = "Used for Thermostat Update Policy",folder = "Functions") ExtractThermostatData {
StageIoTRawData
| where telemetry has 'temp'
| project 
EnqueuedTimeUTC=enqueuedTime,
DeviceId=deviceId,
BatteryLevel = tolong(telemetry.['BatteryLevel']), 
Temp =  toreal(telemetry.['temp']),
Humidity =  toreal(telemetry.['humidity'])
}
```

<img src="gif\IoTCreateFunction.gif" width="740" />

3) Last step is to create the update policy on the Thermastat table. You can use the following command to create the policy:

```
.alter table Thermostats policy update
@'[{"IsEnabled": true, "Source": "StageIoTRawData", "Query": "ExtractThermostatData()", "IsTransactional": false, "PropagateIngestionProperties": false}]'
```

<img src="gif\IoTUpdatePolicy.gif" width="740" />

### Assigning a Service Principal Access
1) [Create a Service Principal](https://docs.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal)
* Take note of the ClientId, TenantId, and the secret that you create
2) Assign the Service Princiapl Table Ingestor rights on the StageIoTRawData table using the following command:

```
.add table  ingestors ('aadapp=<replace_with_ClientId>;<replace_with_TennantId>') 'Test Azure AD App'
```

<img src="gif\IoTIngestor.gif" width="740" />

### Create IoT Central Project ###
1) In the Azure Portal create a new IoT Central Application using the "In-stor Analytics - Condition Monitoring" template. Then open up the IoT Central Application using the link in the portal.

<img src="gif\IoT_CreateIoTCentral.gif" width="740" />  

2) Click on the Devices tab and go to you Thermostat group. Here you can create some demo IoT Thermostats. Make sure when you create them that you choose to simulate the device.

<img src="gif\IoTCreateThermostats.gif" width="740" />  

3) Before creating the export job you can verify that the devices are generating sameple data by clicking on one of the newly created thermostats. You should see data in both the dashboard and the raw tab.

<img src="gif\IoTDeviceTelemetry.gif" width="740" />  

4) Now we can create the data export to Azure Data Explorer. In order to do this you'll need to gather the following information:
- Azured Data Explorer Cluster URL
- Azure Data Explorer Cluster Database
- Table Name (if your following along this will be StageIoTRawData)
- Client ID of your Service Principal
- Tenant ID of your Service Principal
- Secret for your Service Principal

5) Go to the Data Export tab and click on "+ New export". Fill in the following:
- Display Name for the Export
- Data type should be "Telemetry"
- Under destination click on "create a new one". Change the Destination type to "Azure Data Explorer" and fill in the required informaiton

<img src="gif\IoTCreateExport.gif" width="740" />

### Verify Data in ADX
Assuming everything went well you should be able to see data in your ADX tables within 15 minutes. After you take a little break you can run the following to make sure data is present:

- Raw Table
```
StageIoTRawData
| limit 10
```
- Thermostat Table
```
Thermostat
| limit 10
```
<img src="gif\IoTADXResults.gif" width="740" />

## KQL
In this repo you will find some KQL queries that you can run against the thermostat telemetry.

[KQL Demo Queries](https://github.com/bwatts64/ADXIoTDemo/tree/master/iot-lab/kql/ThermostatDemoQueries.kql)

## Summary
You now have a IoT Demo data flowing into your Azure Data Explorer cluster. This is a great way to explore the Kusto Language capabilities or demonstrate this scenerio to others. If your new to Kusto a great place to start is our [documentation!](https://docs.microsoft.com/en-us/azure/data-explorer/kusto/query/)