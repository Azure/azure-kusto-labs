<#
[Microsoft Kusto Lab Project] Creat Databrick Structured Streaming Jobs

Environment Pre-requests: 
    1. Databricks CLI intalled
    2. Azure CLI with Databricks Extension installed
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module1 : Step 2 ===="
Write-Log "INFO"  "====                Deploy Databricks Notebooks                 ====" 
Write-Log "INFO"  "====================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

# Set Constant values
Set-Variable GLOBAL_DATABRICKS_UUID -option Constant -value "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"
Set-Variable DATABRICKS_MANAGEMENT_PORTAL_URL -option Constant -value  "https://management.core.windows.net/"

$db_service =(Get-Resource-Prefix $config.ResourceGroupName)+$config.Databricks.WorkspaceName
Write-Log "INFO"  "Databrcks Service Name: $($db_service)"

# Extract Databrick Workspace Id 
$workspaceId = $(az databricks workspace list --resource-group  $config.ResourceGroupName --query "[?name == '$db_service'].id|[0]")
$workspaceid=$workspaceId -replace '"',''
Write-Log "INFO"  "Databricks Workspace Id: $($workspaceId)"

# Extract Databricks Access Token
$databrickToken=$(az account get-access-token --resource $GLOBAL_DATABRICKS_UUID) |ConvertFrom-Json
$databrickToken=$databrickToken.accessToken
Write-Log "INFO" "Got Databricks Access Token"

# Extract Azure Access Token for Databricks
$azToken=$(az account get-access-token --resource $DATABRICKS_MANAGEMENT_PORTAL_URL ) | ConvertFrom-Json
$azToken=$azToken.accessToken
Write-Log "INFO" "Got Azure Access Token for Databricks"

# Extract Databricks Workspace URL
$workspaceUrl=$(az databricks workspace list --resource-group  $config.ResourceGroupName  --query "[?name == '$db_service'].workspaceUrl|[0]")
$workspaceUrl=$workspaceUrl -replace '"',''
Write-Log "INFO" "Databricks WorkSpacke URL: $($workspaceUrl)" 

#Set Environment Variable for Databricks
[Environment]::SetEnvironmentVariable('DATABRICKS_HOST',"https://"+$workspaceUrl)
[Environment]::SetEnvironmentVariable('DATABRICKS_TOKEN',$databrickToken)

databricks workspace import --language PYTHON --overwrite ../../code/databricks/notebooks/data-preprocessor.py /data-preprocessor.py 

# Cleanup Enivronment Parameters
[Environment]::SetEnvironmentVariable('DATABRICKS_HOST',$null)
[Environment]::SetEnvironmentVariable('DATABRICKS_TOKEN',$null)

Write-Log "INFO" "Deploy Databricks Notebook Successfully!"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }