<#
[Microsoft Kusto Lab Project]
Metadata Handler functions provision
#>

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====   Kusto Lab - Databricks ADX Integration - Module5 : Step 2    ===="
Write-Log "INFO"  "====            Create error-retry Azure Functions                  ====" 
Write-Log "INFO"  "========================================================================" 
#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Azure Function Core Tools, you can use 'func -v' cmd to check"
Write-Log "INFO" "Start to deploy" 

#Set ARM Template File Path
$metadataHandlerfuncTemplatePath = $config.Functions.dbsMetadataHandlerFunction.MetadataHandlerfuncTemplatePath
$metadataHandlerFuncAppsettingTemplatePath = $config.Functions.dbsMetadataHandlerFunction.MetadataHandlerfuncSettingsTemplatePath

#Start Metadatahanlde Function deployment
Write-Log "INFO" "Preparing metadatahanlde Function Parameters....."
$resourceName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.functions.dbsMetadataHandlerFunction.FunctionName

$metadatahandle_func_parameters_str = @{
    FunctionName = $resourceName
    FunctionLocation = $config.Location
}

$metadatahandle_func_parameters = ConvertTo-ARM-Parameters-JSON $metadatahandle_func_parameters_str

#Metadatahandler Function Appsetting Parameters 
$metadatahandle_func_appsetting_parameters_str = @{
    FunctionName = $resourceName
    KeyVaultName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.KeyVaultName
    IngestionStorageAccountName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.IngestionDatalakeName
    IngestionEventQueueName = $config.EventGrid.IngestionEventQueueName
    IngestionConnectingStringName = $config.Functions.IngestionFunction.IngestionConnectingStringName
    IngestionSasTokenName = $config.Functions.dbsMetadataHandlerFunction.IngestionSasTokenName
}

$metadatahandle_func_appsetting_parameters = ConvertTo-ARM-Parameters-JSON $metadatahandle_func_appsetting_parameters_str

Write-Log "INFO" "Start to deploy dbsMetadataHandlerFunctionDeployment" 
Write-Log "INFO" "Before Deploy, metadatahandle_func_parameters = $metadatahandle_func_parameters, metadataHandlerfuncTemplatePath = $metadataHandlerfuncTemplatePath"
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $metadataHandlerFuncTemplatePath $metadatahandle_func_parameters "dbsMetadataHandlerFunctionDeployment"

Write-Log "INFO" "Start to deploy dbsMetadataHandlerFunctionAppSettingDeployment" 
Write-Log "INFO" "Before Deploy, metadatahandle_func_appsetting_parameters = $metadatahandle_func_appsetting_parameters, metadataHandlerFuncAppsettingTemplatePath= $metadataHandlerFuncAppsettingTemplatePath"
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $metadataHandlerFuncAppsettingTemplatePath $metadatahandle_func_appsetting_parameters "dbsMetadataHandlerFunctionAppSettingDeployment"

Write-Log "INFO" "Provision MetaData Handling Function Successfully!"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }