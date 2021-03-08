<#
[Microsoft Kusto Lab Project]
Ingestion functions provision
#>

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module3 : Step 1 ===="
Write-Log "INFO"  "====                Create Ingest Funtions                      ====" 
Write-Log "INFO"  "====================================================================" 


#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Azure Powershell Modules, you can use Get-Module cmd to check modules you installed"
Write-Log "INFO" "Start to deploy" 

#Set ARM Template File Path
$IngestionfuncTemplatePath = $config.Functions.IngestionFunction.IngestionfuncTemplatePath

#Start Function deployment
Write-Log "INFO" "Preparing Ingestion Function Parameters..."
$resourceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Functions.IngestionFunction.FunctionName

Write-Log "INFO" $config.Location
$ingestion_func_strParamValues = @{
    FunctionName=$resourceName
    KeyVaultName=(Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.KeyVaultName
    IngestionStorageAccountName=(Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.IngestionDatalakeName
    IngestionEventQueueName=$config.EventGrid.IngestionEventQueueName
    IngestionConnectingStringName=$config.Functions.IngestionFunction.IngestionConnectingStringName
    LeadClusterName=(Get-Resource-Prefix $config.ResourceGroupName)+$config.ADX.ClusterName
    FunctionLocation=$config.Location
    Runtime=$config.Functions.IngestionFunction.Runtime
    DatabaseIDKey=$config.Functions.IngestionFunction.DatabaseIDKey
    TableIDKey=$config.Functions.IngestionFunction.TableIDKey
    IsFlushImmediately=$config.Functions.IngestionFunction.IsFlushImmediately
    IsDuplicateCheck=$config.Functions.IngestionFunction.IsDuplicateCheck
 }
$ingestion_func_objParamValues = @{
    IngestionEventQueueCount=$config.EventGrid.IngestionEventQueueCount
 }
$ingestion_func_parameters = ConvertTo-ARM-Parameters-JSON $ingestion_func_strParamValues  $ingestion_func_objParamValues  

Write-Log "INFO" "Before Deploy, ingestion_func_parameters = $ingestion_func_parameters"
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $IngestionfuncTemplatePath $ingestion_func_parameters "IngestionFunctionDeployment"

#Update KeyVault Access Policy for Function
$funresourceName =$resourceName+'0'

$update_keyvault_access_parameters_str = @{
    FunctionName = $funresourceName
    KeyVaultName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.KeyVaultName
}
$update_keyvault_access_parameters = ConvertTo-ARM-Parameters-JSON $update_keyvault_access_parameters_str
Write-Log "INFO" "Before update, update_keyvault_access_parameters = $update_keyvault_access_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $funresourceName $config.ResourceGroupName $config.KeyVault.KeyVaultAccessTemplatePath $update_keyvault_access_parameters "KeyVaultAccessPolicyUpdate"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }