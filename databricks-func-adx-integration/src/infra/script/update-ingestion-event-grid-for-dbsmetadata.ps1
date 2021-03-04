<#
[Microsoft Kusto Lab Project]
Module 6 Update Event Grid Subscription & Storage Queue for exactly once ingestion
#>

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module 6 : Step 1 ===="
Write-Log "INFO"  "====      Update Event Grid Subscription & Storage Queue         ====" 
Write-Log "INFO"  "=====================================================================" 


#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Create Resouce Group First
Write-Log "INFO" "Creating/Assign Resource Group for Deployment" 
az group create -l $config.Location -n $config.ResourceGroupName

Write-Log "INFO" "Preparing Ingestion Storage Event Grid Parameters....."
$resourceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.IngestionDatalakeName
Write-Log "INFO" $resourceName

#Compose Event Grid Subscription Filter Rule
$dbsMetadataEventFilterAry = Set-EventGrid-Filter $config.EventGrid.DBSMetadataEventFilters
Write-Log "INFO" "dbsMetadataEventFilterAry = $dbsMetadataEventFilterAry"

$dbs_metadata_event_grid_strParamValues = @{
    EventSubName=$resourceName+"-subscription"
    TopicStorageAccountName=$resourceName
    SubStorageAccountName=$resourceName
    SubQueueName=$config.EventGrid.DBSMetadataQueueName
    Location=$config.Location
    TriggerContainerName=$config.Storage.FileSystemName
    TirggerFolderName=$config.Storage.AzureStorageTargetFolder
    EventType=$config.EventGrid.EventTypeRenamed
}
$dbs_metadata_event_grid_objParamValues = @{
    EventQueueCount=$config.EventGrid.DBSMetadataQueueCount
    DefaultFilters=$dbsMetadataEventFilterAry
    IsFunctionTriggerSource=$true
}
$dbs_metadata_event_grid_parameters = ConvertTo-ARM-Parameters-JSON $dbs_metadata_event_grid_strParamValues $dbs_metadata_event_grid_objParamValues  

Write-Log "INFO" "Before Deploy, dbs_metadata_event_grid_parameters = $dbs_metadata_event_grid_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.EventGrid.EventGridTemplatePath $dbs_metadata_event_grid_parameters "DBSMetadataEventGridDeployment"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }