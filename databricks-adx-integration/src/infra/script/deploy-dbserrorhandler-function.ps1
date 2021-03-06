<#
[Microsoft Kusto Lab Project]
DBS error handler Function Deploy
#>

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"


Write-Log "INFO"  "====   Kusto Lab - Databricks ADX Integration - Module5 : Step  3-1        ===="
Write-Log "INFO"  "====            Deploy Databricks Error-Handler  Azure Functions           ====" 
Write-Log "INFO"  "===============================================================================" 

#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Start Resource Deployement
Write-Log "INFO" "Before deployment, please make sure you have installed the Azure Function Core Tools, you can use 'func -v' cmd to check, or you can using 
'npm install -g azure-functions-core-tools' to install it"
Write-Log "INFO" "Start to deploy dbserrorhandleFunctionDeployment" 
$path = $config.functions.dbsErrorHandlerFunction.Path
$functionFolder = $config.functions.dbsErrorHandlerFunction.FunctionName
$triggerQueueName = $config.EventGrid.DataBricksErrorHandlingQueueName
$resourceName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.functions.dbsErrorHandlerFunction.FunctionName

Publish-Azure-Function-Deployment $path $functionFolder $triggerQueueName $resourceName

Write-Log "INFO" "Deploy DBS error handler Function Successfully!"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }
