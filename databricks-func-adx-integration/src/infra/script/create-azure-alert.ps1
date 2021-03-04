<#
[Microsoft Kusto Lab Project]
Monitor Module resource provisioning
1. Including the provisioning the following resources:
   a. Alerts for ADX Cluster
   b. Alerts for Datalake
   c. Alerts for EventGrid
   d. Alerts for Ingestion Function (Azure Function)
   e. Alerts for DBS and ADX error handling Function (Azure Function)
#>
#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module7 : Step 5 ===="
Write-Log "INFO"  "====              Create Azure Alert                            ====" 
Write-Log "INFO"  "====================================================================" 


#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Start Action Group deployment
Write-Log "INFO" "Preparing Action Group Parameters....."
$actionGrpName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.AzureMonitor.ActionGroup.Name
Write-Log "INFO" $actionGrpName

$action_group_parameters_str = @{
    ActionGroupName= $actionGrpName
    ActionGroupShortName =$config.AzureMonitor.ActionGroup.ShortName 
    EmailGroupName =$config.AzureMonitor.ActionGroup.EmailGroupName
    EmailRecipients =$config.AzureMonitor.ActionGroup.EmailRecipients
    AzureOpsGenieAPIUrl =$config.AzureMonitor.ActionGroup.AzureOpsGenieAPIUrl
    AzureOpsGenieAPIKey =$config.AzureMonitor.ActionGroup.AzureOpsGenieAPIKey
}

$action_group_parameters = ConvertTo-ARM-Parameters-JSON $action_group_parameters_str 

Write-Log "INFO" "Before Deploy, action_group_parameters = $action_group_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $actionGrpName $config.ResourceGroupName $config.AzureMonitor.ActionGroup.ActionGroupTemplatePath $action_group_parameters "ActionGroupDeployment"

#Start ADX Alert Deployment
Write-Log "INFO" "Preparing ADX Alert Parameters....."
$alertName = "ADXAlert"
$adx_alert_parameters_str = @{
    ActionGroupName= (Get-Resource-Prefix $config.ResourceGroupName)+$config.AzureMonitor.ActionGroup.Name
    Cluster =(Get-Resource-Prefix $config.ResourceGroupName)+$config.ADX.ClusterName
    ResourceGroup =$config.ResourceGroupName
}
$adx_alert_parameters_num = @{    
    ADXClusterHighCPUThreshold =$config.AzureMonitor.ADXAlert.ADXClusterHighCPUThreshold
    ADXClusterHighIngestionLatencyThreshold =$config.AzureMonitor.ADXAlert.ADXClusterHighIngestionLatencyThreshold
    ADXClusterHighIngestionUtilThreshold =$config.AzureMonitor.ADXAlert.ADXClusterHighIngestionUtilThreshold
}

$adx_alert_parameters = ConvertTo-ARM-Parameters-JSON $adx_alert_parameters_str $adx_alert_parameters_num

Write-Log "INFO" "Before Deploy, adx_alert_parameters = $adx_alert_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $alertName $config.ResourceGroupName $config.AzureMonitor.ADXAlert.ADXAlertTemplatePath $adx_alert_parameters "ADXAlertDeployment"

#Start Datalake Alert deployment
Write-Log "INFO" "Preparing Datalake Alert Parameters....."
$alertName = "DatalakeAlert"
$datalake_alert_parameters_str = @{
    ActionGroupName= (Get-Resource-Prefix $config.ResourceGroupName)+$config.AzureMonitor.ActionGroup.Name
    LandingStorageAccountName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.LandingDatalakeName
    ResourceGroup =$config.ResourceGroupName
}

$datalake_alert_parameters_num = @{
    DatalakeLowIngressThreshold = $config.AzureMonitor.DatalakeAlert.DatalakeLowIngressThreshold
}

$datalake_alert_parameters = ConvertTo-ARM-Parameters-JSON $datalake_alert_parameters_str $datalake_alert_parameters_num 

Write-Log "INFO" "Before Deploy, datalake_alert_parameters = $datalake_alert_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $alertName $config.ResourceGroupName $config.AzureMonitor.DatalakeAlert.DatalakeAlertTemplatePath $datalake_alert_parameters "DatalakeAlertDeployment"

#Start EventGrid Alert deployment
Write-Log "INFO" "Preparing Event Grid Alert Parameters....."
$alertName = "EventGridAlert"
$eventgrid_alert_parameters_str = @{
    ActionGroupName= (Get-Resource-Prefix $config.ResourceGroupName)+$config.AzureMonitor.ActionGroup.Name
    EventGridSystemTopicName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.LandingDatalakeName
    ResourceGroup =$config.ResourceGroupName
}

$eventgrid_alert_parameters_num = @{
    EventGridLowPublishedThreshold = $config.AzureMonitor.EventGridAlert.EventGridLowPublishedThreshold
    EventGridHighDroppedThreshold = $config.AzureMonitor.EventGridAlert.EventGridHighDroppedThreshold
}

$eventgrid_alert_parameters = ConvertTo-ARM-Parameters-JSON $eventgrid_alert_parameters_str $eventgrid_alert_parameters_num 

Write-Log "INFO" "Before Deploy, eventgrid_alert_parameters = $eventgrid_alert_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $alertName $config.ResourceGroupName $config.AzureMonitor.EventGridAlert.EventGridAlertTemplatePath $eventgrid_alert_parameters "EventGridAlertDeployment"

#Start Ingestion Function Alert deployment
Write-Log "INFO" "Preparing Ingestion Function Alert Parameters....."
$alertName = "IngestionFunctionAlert"
$ingestion_func_alert_parameters_str = @{
    ActionGroupName= (Get-Resource-Prefix $config.ResourceGroupName)+$config.AzureMonitor.ActionGroup.Name
    AzFunctionName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Functions.IngestionFunction.FunctionName
    ResourceGroup =$config.ResourceGroupName
}

$ingestion_func_alert_parameters_num = @{
    IngestionFuncNotTriggerThreshold = $config.AzureMonitor.FunctionAlert.IngestionFuncNotTriggerThreshold
    IngestionEventQueueCount = $config.EventGrid.IngestionEventQueueCount
}

$ingestion_func_alert_parameters = ConvertTo-ARM-Parameters-JSON $ingestion_func_alert_parameters_str $ingestion_func_alert_parameters_num 

Write-Log "INFO" "Before Deploy, ingestion_func_alert_parameters = $ingestion_func_alert_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $alertName $config.ResourceGroupName $config.AzureMonitor.FunctionAlert.IngestionFuncAlertTemplatePath $ingestion_func_alert_parameters "IngestionFuncAlertDeployment"

#Start Error Handling Function Alert deployment
Write-Log "INFO" "Preparing Error Handling Function Alert Parameters....."
$alertName = "ErrorHandlingFuncAlert"
$errorHandling_func_alert_parameters_str = @{
    ResourceGroup = $config.ResourceGroupName
    ActionGroupName= $actionGrpName
    AzFunctionName1 = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Functions.adxErrorHandlerFunction.FunctionName
    AzFunctionName2 = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Functions.dbsErrorHandlerFunction.FunctionName
}

$errorHandling_func_alert_parameters_num = @{
    ErrorHandlingAlertTriggerThreshold = $config.AzureMonitor.FunctionAlert.ErrorHandlingAlertTriggerThreshold
    IngestionEventQueueCount = $config.EventGrid.IngestionEventQueueCount
}

$errorHandling_func_alert_parameters = ConvertTo-ARM-Parameters-JSON $errorHandling_func_alert_parameters_str $errorHandling_func_alert_parameters_num 

Write-Log "INFO" "Before Deploy, errorHandling_func_alert_parameters = $errorHandling_func_alert_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $alertName $config.ResourceGroupName $config.AzureMonitor.FunctionAlert.ErrorHandlingFuncAlertTemplatePath $errorHandling_func_alert_parameters "ErrorHandlingFuncAlertDeployment"

Write-Log "INFO" "Deploy Azure Alerts successfully!"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }