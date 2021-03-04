<#
[Microsoft Kusto Lab Project]
Error Handlering Module resource provisioning
1. Including the provisioning the following resources:
   Event Grid Subscription & Queues for ADX ingestion function error handling
   Event Grid Subscription & Queues for DBS bad request error handling
#>

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====   Kusto Lab - Databricks ADX Integration - Module5 : Step 1           ===="
Write-Log "INFO"  "====            Create  Error-Retry Event Grid                             ====" 
Write-Log "INFO"  "===============================================================================" 


#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Create Resouce Group First
Write-Log "INFO" "Creating/Assign Resource Group for Deployment" 
az group create -l $config.Location -n $config.ResourceGroupName

#Start Event Grid deployment
Write-Log "INFO" "Preparing Landing Storage Databricks Bad Record Evnet Grid Parameters....."
$resourceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.LandingDatalakeName
Write-Log "INFO" $resourceName

#Compose Landing Storage Bad Record Subscription Filter Rule
$badRequestsfilterAry = Set-EventGrid-Filter $config.EventGrid.BadRequestsFilters
$badRequestsAdvancedfilterAry = Set-EventGrid-Filter $config.EventGrid.BadRequestsAdvancedFilters
#TODO:Add Set-Advance-EventGrid_Filter to process multiple advance filters
$badRequestsAdvancedfilterAry = '{\"filters\":' + $badRequestsAdvancedfilterAry + '}'

Write-Log "INFO" "badRequestsfilterAry = $badRequestsfilterAry `n badRequestsAdvancedfilterAry = $badRequestsAdvancedfilterAry"

$landing_storage_badrecords_event_grid_strParamValues = @{
    EventSubName=$resourceName+"-badrequests-subscription"
    TopicStorageAccountName=$resourceName
    SubStorageAccountName=$resourceName
    SubQueueName=$config.EventGrid.DataBricksErrorHandlingQueueName
    Location=$config.Location
    TriggerContainerName=$config.Storage.FileSystemName
    TirggerFolderName=$config.Storage.LandingBadRecordFolder
    EventType=$config.EventGrid.EventTypeCreate
}
$landing_storage_badrecords_event_grid_objParamValues = @{
    EventQueueCount=$config.EventGrid.BadRequestsQueueCount
    DefaultFilters=$badRequestsfilterAry
    AdvancedFilters=$badRequestsAdvancedfilterAry
    IsFunctionTriggerSource=$false
}
$landing_storage_badrecords_event_grid_parameters = ConvertTo-ARM-Parameters-JSON $landing_storage_badrecords_event_grid_strParamValues $landing_storage_badrecords_event_grid_objParamValues  

Write-Log "INFO" "Before Deploy, landing_storage_badrecords_event_grid_parameters = $landing_storage_badrecords_event_grid_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.EventGrid.EventGridTemplatePath $landing_storage_badrecords_event_grid_parameters "LandingBadRecordsEventGridDeployment"

Write-Log "INFO" "Preparing Ingestion Storage Error Handling Event Grid Parameters....."
$resourceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.IngestionDatalakeName
Write-Log "INFO" $resourceName

#Compose Event Grid Subscription Filter Rule
$adxIngestionErrorHandlingEventFilterAry = Set-EventGrid-Filter $config.EventGrid.IngestionRetryEventFilters
$adxIngestionErrorHandlingEventAdvancedFilterAry = Set-EventGrid-Filter $config.EventGrid.IngestionRetryEventAdvancedFilters
$adxIngestionErrorHandlingEventAdvancedFilterAry = '{\"filters\":' + $adxIngestionErrorHandlingEventAdvancedFilterAry + '}'
Write-Log "INFO" "adxIngestionErrorHandlingEventFilterAry = $adxIngestionErrorHandlingEventFilterAry"

$ingestion_error_handling_event_grid_strParamValues = @{
    EventSubName=$resourceName+"-retry-subscription"
    TopicStorageAccountName=$resourceName
    SubStorageAccountName=$resourceName
    SubQueueName=$config.EventGrid.IngestionEventQueueName
    Location=$config.Location
    TriggerContainerName=$config.Storage.FileSystemName
    TirggerFolderName=$config.Storage.AzureStorageTargetFolder
    EventType=$config.EventGrid.EventTypeCreate
}
$ingestion_error_handling_event_grid_objParamValues = @{
    EventQueueCount=$config.EventGrid.IngestionEventQueueCount
    DefaultFilters=$adxIngestionErrorHandlingEventFilterAry
    AdvancedFilters=$adxIngestionErrorHandlingEventAdvancedFilterAry
    IsFunctionTriggerSource=$true
}
$ingestion_error_handling_event_grid_parameters = ConvertTo-ARM-Parameters-JSON $ingestion_error_handling_event_grid_strParamValues $ingestion_error_handling_event_grid_objParamValues  

Write-Log "INFO" "Before Deploy, ingestion_error_handling_event_grid_parameters = $ingestion_error_handling_event_grid_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.EventGrid.EventGridTemplatePath $ingestion_error_handling_event_grid_parameters "IngestionErrorHandlingEventGridDeployment"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }