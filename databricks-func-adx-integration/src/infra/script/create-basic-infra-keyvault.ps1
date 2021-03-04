<#
[Microsoft Kusto Lab Project]
Basic infra resource provisioning
1. Including the provisioning the following resources:  
   Azure Key Vault:
   Azure Function Related Key Vault
   Databricks Related Key Vault
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module0 : Step 3 ===="
Write-Log "INFO"  "====                   Create Key Vault                         ====" 
Write-Log "INFO"  "====================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Start Key Vault deployment
Write-Log "INFO" "Preparing Function Key Vault Parameters....."
$resourceName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.KeyVaultName
Write-Log "INFO" $resourceName


$function_keyvault_strParamValues = @{
    KeyVaultName=$resourceName
    Location=$config.Location
    AadObjectId=$config.DeployObjectId
}
$function_keyvault_numParamValues = @{
    SoftDelete=$config.KeyVault.SoftDelete
}
$function_keyvault_parameters = ConvertTo-ARM-Parameters-JSON $function_keyvault_strParamValues $function_keyvault_numParamValues  
Write-Log "INFO" "Before Deploy, function_keyvault_parameters = $function_keyvault_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.KeyVault.KeyVaultTemplatePath $function_keyvault_parameters "KeyVaultDeployment"

Write-Log "INFO" "Preparing Databricks Key Vault Parameters....."
$resourceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.DatabricksKeyVaultName
Write-Log "INFO" $resourceName

$databricks_keyvault_strParamValues = @{
    KeyVaultName=$resourceName
    Location=$config.Location
    AadObjectId=$config.DeployObjectId
}
$databricks_keyvault_numParamValues = @{
    SoftDelete=$config.KeyVault.SoftDelete
}
$databricks_keyvault_parameters = ConvertTo-ARM-Parameters-JSON $databricks_keyvault_strParamValues $databricks_keyvault_numParamValues  

Write-Log "INFO" "Before Deploy, databricks_keyvault_parameters = $databricks_keyvault_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.KeyVault.KeyVaultTemplatePath $databricks_keyvault_parameters "DatabricksKeyVaultDeployment"
   
# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }