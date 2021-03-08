<#
[Microsoft Kusto Lab Project]
Errorhandling functions provision
#>

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====   Kusto Lab - Databricks ADX Integration - Module5 : Step 2           ===="
Write-Log "INFO"  "====            Create  Error-Retry Azure Functions                        ====" 
Write-Log "INFO"  "===============================================================================" 

#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Azure Powershell Modules, you can use Get-Module cmd to check modules you installed"
Write-Log "INFO" "Start to deploy" 

#Set ARM Template File Path
$DbserrorhandlefuncTemplatePath = $config.functions.dbsErrorHandlerFunction.DbserrorhandlefuncTemplatePath
$DbserrorhandleFuncAppsettingTemplatePath = $config.functions.dbsErrorHandlerFunction.DbserrorhandleFuncAppsettingTemplatePath
$AdxerrorhandlefuncTemplatePath = $config.functions.adxErrorHandlerFunction.AdxerrorhandlefuncTemplatePath

#Start dbserrorhandle Function deployment
Write-Log "INFO" "Preparing dbserrorhandle Function Parameters....."
$resourceName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.functions.dbsErrorHandlerFunction.FunctionName
#Prepare dbserrorhandle fucntion parameters
$dbserrorhandle_func_parameters_str = @{
    FunctionName = $resourceName
    FunctionLocation = $config.Location
}

$dbserrorhandle_func_parameters = ConvertTo-ARM-Parameters-JSON $dbserrorhandle_func_parameters_str 

#Prepare dbserrorhandle fucntion app settings parameters
$dbserrorhandle_func_appsetting_parameters_str = @{
    FunctionName = $resourceName
    KeyVaultName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.KeyVaultName
    FinalFailedFolder = $config.Storage.FinalFailedFolder
}

$dbserrorhandle_func_appsetting_parameters = ConvertTo-ARM-Parameters-JSON $dbserrorhandle_func_appsetting_parameters_str

Write-Log "INFO" "Start to deploy dbserrorhandleFunctionDeployment" 
Write-Log "INFO" "Before Deploy, dbserrorhandle_func_parameters = $dbserrorhandle_func_parameters"
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $DbserrorhandlefuncTemplatePath $dbserrorhandle_func_parameters "dbserrorhandleFunctionDeployment"


Write-Log "INFO" "Start to deploy dbserrorhandleFunctionAppSetting" 
Write-Log "INFO" "Before Deploy, dbserrorhandle_func_appsetting_parameters = $dbserrorhandle_func_appsetting_parameters"
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $DbserrorhandleFuncAppsettingTemplatePath $dbserrorhandle_func_appsetting_parameters "dbserrorhandleFunctionAppSettingDeployment"


#Start adxerrorhandle Function deployment
Write-Log "INFO" "Preparing adxerrorhandle Function Parameters....."
$resourceName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.functions.adxErrorHandlerFunction.FunctionName
$adxerrorhandle_func_parameters_str = @{
    FunctionName = $resourceName
    KeyVaultName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.KeyVaultName
    FunctionLocation = $config.Location
    Runtime = $config.Functions.adxErrorHandlerFunction.Runtime
    FinalFailedContainer = $config.Storage.IngestionRetryEndInFailContainerName
    IngestionFunctionName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Functions.IngestionFunction.FunctionName
}

$adxerrorhandle_func_parameters_num = @{
    IngestionEventQueueCount = $config.EventGrid.IngestionEventQueueCount
}

$adxerrorhandle_func_parameters = ConvertTo-ARM-Parameters-JSON $adxerrorhandle_func_parameters_str $adxerrorhandle_func_parameters_num

Write-Log "INFO" "Start to deploy adxerrorhandleFunctionDeployment" 
Write-Log "INFO" "Before Deploy, adxerrorhandle_func_parameters = $adxerrorhandle_func_parameters"
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $AdxerrorhandlefuncTemplatePath $adxerrorhandle_func_parameters "adxerrorhandleFunctionDeployment"


#Update KeyVault Access Policy for Function
$resourceName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.Functions.adxErrorHandlerFunction.FunctionName+'0'

$update_keyvault_access_parameters_str = @{
    FunctionName = $resourceName
    KeyVaultName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.KeyVaultName
}

$update_keyvault_access_parameters = ConvertTo-ARM-Parameters-JSON $update_keyvault_access_parameters_str

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.KeyVault.KeyVaultAccessTemplatePath $update_keyvault_access_parameters "KeyVaultAccessPolicyUpdate"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }