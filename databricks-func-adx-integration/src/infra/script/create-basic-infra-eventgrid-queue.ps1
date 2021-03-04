<#
[Microsoft Kusto Lab Project]
Basic infra resource provisioning
1. Including the provisioning the following resources:
   Event Grid:
   Ingestion Data Grid and Related Storage Queues
   Landing Data Grid and Related Storage Queues
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module0 : Step 2 ===="
Write-Log "INFO"  "====           Create Event Grid & Storage Queue                ====" 
Write-Log "INFO"  "====================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

# Deploy Landing EventGrid  =======================================
Write-Log "INFO" "Preparing Landing Event Grid Parameters....."
$resourceName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.LandingDatalakeName
Write-Log "INFO" $resourceName

#Compose Event Grid Subscription Filter Rule
$landingEventFilterAry = Set-EventGrid-Filter $config.EventGrid.LandingEventFilters
Write-Log "INFO" "landingEventFilterAry = $landingEventFilterAry"

$landing_event_grid_strParamValues = @{
    EventSubName=$resourceName+"-subscription"
    TopicStorageAccountName=$resourceName
    SubStorageAccountName=$resourceName
    SubQueueName=$config.EventGrid.LandingEventQueueName
    Location=$config.Location
    TriggerContainerName=$config.Storage.FileSystemName
    TirggerFolderName=$config.Storage.FileSystemNameRootFolder
    EventType=$config.EventGrid.EventTypeCreate
}
$landing_event_grid_objParamValues = @{
    EventQueueCount=$config.EventGrid.LandingEventQueueCount
    DefaultFilters=$landingEventFilterAry
    IsFunctionTriggerSource=$false
}


$landing_event_grid_parameters = ConvertTo-ARM-Parameters-JSON $landing_event_grid_strParamValues $landing_event_grid_objParamValues  
Write-Log "INFO" "Before Deploy, landing_event_grid_parameters = $landing_event_grid_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.EventGrid.EventGridTemplatePath $landing_event_grid_parameters "LandingEventGridDeployment"

# Deploy Ingestion EventGrid  =======================================
Write-Log "INFO" "Preparing Ingestion Event Grid Parameters....."
$resourceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.IngestionDatalakeName
Write-Log "INFO" " $resourceName"

#Compose Event Grid Subscription Filter Rule
$ingestionEventFilterAry = Set-EventGrid-Filter $config.EventGrid.IngestionEventFilters
$IngestionEventAdvancedFilterAry = Set-EventGrid-Filter $config.EventGrid.IngestionEventAdvancedFilters
#TODO:Add Set-Advance-EventGrid_Filter to process multiple advance filters
$IngestionEventAdvancedFilterAry = '{\"filters\":' + $IngestionEventAdvancedFilterAry + '}'
Write-Log "INFO" "ingestionEventFilterAry = $ingestionEventFilterAry"

$ingestion_event_grid_strParamValues = @{
    EventSubName=$resourceName+"-subscription"
    TopicStorageAccountName=$resourceName
    SubStorageAccountName=$resourceName
    SubQueueName=$config.EventGrid.IngestionEventQueueName
    Location=$config.Location
    TriggerContainerName=$config.Storage.FileSystemName
    TirggerFolderName=$config.Storage.AzureStorageTargetFolder
    EventType=$config.EventGrid.EventTypeCreate
}
$ingestion_event_grid_objParamValues = @{
    EventQueueCount=$config.EventGrid.IngestionEventQueueCount
    DefaultFilters=$ingestionEventFilterAry
    AdvancedFilters=$IngestionEventAdvancedFilterAry
    IsFunctionTriggerSource=$true
}
$ingestion_event_grid_parameters = ConvertTo-ARM-Parameters-JSON $ingestion_event_grid_strParamValues $ingestion_event_grid_objParamValues  

Write-Log "INFO" "Before Deploy, ingestion_event_grid_parameters = $ingestion_event_grid_parameters"


#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.EventGrid.EventGridTemplatePath $ingestion_event_grid_parameters "IngestionEventGridDeployment"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }