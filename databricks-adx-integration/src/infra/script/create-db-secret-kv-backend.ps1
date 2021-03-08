
#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====   Kusto Lab - Databricks ADX Integration - Module7 : Step 2-1  ===="
Write-Log "INFO"  "====   Create Databricks Secrete Scope with Azure KeyValue BackEnd  ====" 
Write-Log "INFO"  "========================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

Write-Log "INFO" "Connect to Azure using an account that can create Service Principal" 
# Connect to Azure
az login

# Set Constant values
Set-Variable GLOBAL_DATABRICKS_UUID -option Constant -value "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"
Set-Variable DATABRICKS_MANAGEMENT_PORTAL_URL -option Constant -value  "https://management.core.windows.net/"

$db_service = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Databricks.WorkspaceName
Write-Log "INFO"  "Databrcks Service Name: $($db_service)"

# Extract Databrick Workspace Id 
$workspaceId = $(az databricks workspace list --resource-group  $config.ResourceGroupName --query "[?name == '$db_service'].id|[0]")
$workspaceid=$workspaceId -replace '"',''
Write-Log "INFO"  "Databricks Workspace Id: $($workspaceId)"

# Extract Databricks Access Token
$databrickToken=$(az account get-access-token --resource $GLOBAL_DATABRICKS_UUID) |ConvertFrom-Json
$databrickToken=$databrickToken.accessToken
Write-Log "INFO" "Got Databricks Access Token"


# Extract Databricks Workspace URL
$workspaceUrl=$(az databricks workspace list --resource-group  $config.ResourceGroupName  --query "[?name == '$db_service'].workspaceUrl|[0]")
$workspaceUrl=$workspaceUrl -replace '"',''
Write-Log "INFO" "Databricks WorkSpacke URL: $($workspaceUrl)" 


#Set Environment Variable for Databricks
[Environment]::SetEnvironmentVariable('DATABRICKS_HOST',"https://"+$workspaceUrl)
[Environment]::SetEnvironmentVariable('DATABRICKS_TOKEN',$databrickToken)

$keyvalutId="/subscriptions/$($config.AzureSubscriptionId)/resourceGroups/$($config.ResourceGroupName)/providers/Microsoft.KeyVault/vaults/$((Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.DatabricksKeyVaultName)"
$keyvalutDNS="https://$((Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.DatabricksKeyVaultName).vault.azure.net/"

# Create Job Parameters Config Files
$scopeNameCount = (databricks secrets list-scopes| select-string -pattern $config.LogAnalytics.SecretScope).length
Write-Log "INFO" "Find $($scopeNameCount) Databricks secret scope named $($config.LogAnalytics.SecretScope)"
if ($scopeNameCount -eq 0){
    Write-Log "INFO" "Didn't find Databricks Secret Scope $($config.LogAnalytics.SecretScope) in Databricks, start creating Azure KeyVault backend sceret-scope"
    databricks secrets create-scope --scope $config.LogAnalytics.SecretScope --scope-backend-type AZURE_KEYVAULT --resource-id $keyvalutId --dns-name $keyvalutDNS --initial-manage-principal users
    $scopeNameCount = (databricks secrets list-scopes| select-string -pattern $config.LogAnalytics.SecretScope).length
    if ($scopeNameCount="1"){
        Write-Log "INFO" "Successfully Created Azure KeyValt-Backended Secret Scope $($config.LogAnalytics.SecretScope) in Databricks"
    }
} else {
    Write-Log "INFO" "Found existed Databricks Secret Scope $($config.LogAnalytics.SecretScope), Skip Creating"
}


# Cleanup Enivronment Parameters
[Environment]::SetEnvironmentVariable('DATABRICKS_HOST',$null)
[Environment]::SetEnvironmentVariable('DATABRICKS_TOKEN',$null)

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }