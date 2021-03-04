#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration  ===="
Write-Log "INFO"  "====           Prepare Databricks CLI Evn               ====" 
Write-Log "INFO"  "====================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

$db_service =(Get-Resource-Prefix $config.ResourceGroupName)+$config.Databricks.WorkspaceName
Write-Log "INFO"  "Databrcks Service Name: $($db_service)"

# Extract Databricks Workspace URL
$workspaceUrl=$(az databricks workspace list --resource-group  $config.ResourceGroupName  --query "[?name == '$db_service'].workspaceUrl|[0]")
$workspaceUrl=$workspaceUrl -replace '"',''
Write-Log "INFO" "Databricks WorkSpacke URL: $($workspaceUrl)" 

# Extract Databrick Workspace Id 
$workspaceId = $(az databricks workspace list --resource-group  $config.ResourceGroupName --query "[?name == '$db_service'].id|[0]")
$workspaceid=$workspaceId -replace '"',''
Write-Log "INFO"  "Databricks Workspace Id: $($workspaceId)"

# Set Constant values
Set-Variable GLOBAL_DATABRICKS_UUID -option Constant -value "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"
Set-Variable DATABRICKS_MANAGEMENT_PORTAL_URL -option Constant -value  "https://management.core.windows.net/"

# Extract Databricks Access Token
$databrickToken=$(az account get-access-token --resource $GLOBAL_DATABRICKS_UUID) |ConvertFrom-Json
$databrickToken=$databrickToken.accessToken
Write-Log "INFO" "Got Databricks Access Token"

# Extract Azure Access Token for Databricks
$azToken=$(az account get-access-token --resource $DATABRICKS_MANAGEMENT_PORTAL_URL ) | ConvertFrom-Json
$azToken=$azToken.accessToken
Write-Log "INFO" "Got Azure Access Token for Databricks"

$authToken="Bearer $databrickToken"
Write-Log "INFO" "Got Auth Token for Databricks"

$header = @{
      "Accept"="application/json"
      "Authorization"=$authToken
      "X-Databricks-Azure-SP-Management-Token"=$azToken
      "X-Databricks-Azure-Workspace-Resource-Id"=$workspaceId
      "Content-Type"="application/json"
   } 

$databricksUrl="https://$($workspaceUrl)/api/2.0/token/create"
Write-Log "INFO" "databricksUrl = $databricksUrl"
$body=@{ lifetime_seconds= 600; comment= "this is an example token" }| ConvertTo-Json -Compress
$databricks_token=(Invoke-WebRequest -Headers $header `
                  -Method POST `
                  -Body $body `
                  -Uri $databricksUrl `
                  -ContentType application/json )    |ConvertFrom-Json
   
$dbsPAT=$databricks_token.token_value   
Write-Log "INFO" "Got Personal Access Token for Databricks"

#Set Environment Variable for Databricks
[Environment]::SetEnvironmentVariable('DATABRICKS_HOST',"https://"+$workspaceUrl)
[Environment]::SetEnvironmentVariable('DATABRICKS_TOKEN',$dbsPAT)
