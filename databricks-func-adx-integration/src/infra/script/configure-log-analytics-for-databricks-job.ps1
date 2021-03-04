<#
[Microsoft Kusto Lab Project] Setup Log Analytics for DBS
Environment Pre-requests: 
    1. Databricks CLI intalled
    2. Azure CLI with Databricks Extension installed
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module7 : Step 3-1 ===="
Write-Log "INFO"  "====           Setup Log Analytics For Databricks               ====" 
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

Write-Log "INFO" "Prepare Setup Databricks-backed Secret Scope for Log Analytics"
#Get Log Analytics Workspace ID and Shared Key
$logAnalyticsWorkspaceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.LogAnalytics.WorkspaceName
$logAnalyticsWorkspaceId = ($(az monitor log-analytics workspace show --resource-group $config.ResourceGroupName --workspace-name $logAnalyticsWorkspaceName) | ConvertFrom-Json).customerId
$logAnalyticsWorkspacePrimaryKey = ($(az monitor log-analytics workspace get-shared-keys --resource-group $config.ResourceGroupName --subscription $config.AzureSubscriptionId --workspace-name $logAnalyticsWorkspaceName) | ConvertFrom-Json).primarySharedKey

#Use Databrick-Cli create Databricks-backed secret scope for log analytics and list the created secret scope
databricks secrets create-scope --scope $config.LogAnalytics.SecretScope --initial-manage-principal users
databricks secrets list-scopes

#put log analytics id and key into secret
databricks secrets put --scope $config.LogAnalytics.SecretScope --key $config.LogAnalytics.SecretScopeKeyWorkspaceId --string-value $logAnalyticsWorkspaceId
databricks secrets put --scope $config.LogAnalytics.SecretScope --key $config.LogAnalytics.SecretScopeKeyWorkspaceKey --string-value $logAnalyticsWorkspacePrimaryKey
databricks secrets list --scope $config.LogAnalytics.SecretScope
Write-Log "INFO" "Complete Setup Databricks-backed Secret Scope for Log Analytics"

Write-Log "INFO" "Prepare Setup Spark-Monitoring Script Parameters"
# SET Spark Monitoring Script Parameters
$ParamValues = @{
    subscription_id_param= $config.AzureSubscriptionId
    group_name_param =$config.ResourceGroupName
    db_workspace_name_param =$config.Databricks.WorkspaceName
}

$sparkMonitoringScript = $config.LogAnalytics.SparkMonitoringScript
$sparkMonitoringScriptTemplate = "../Azure/databricks-monitoring/spark-monitoring.sh.template"

#Create a directory for the spark monitoring related libs
dbfs mkdirs dbfs:/databricks/spark-monitoring
#Copy spark-monitoring.sh template to the destination directory
Copy-Item $sparkMonitoringScriptTemplate $sparkMonitoringScript

# Setup Spark Moniroting Parameters
$ScriptContent = Get-Content -Path $sparkMonitoringScript -Raw 
$paramValues.keys | ForEach-Object{
    $ScriptContent=$ScriptContent -replace $_, $paramValues[$_]
}

$ScriptContent=$ScriptContent.Replace("`r`n","`n") 
Set-Content -Path $sparkMonitoringScript -Value $ScriptContent  -NoNewline

Write-Log "INFO" "Prepare Copy Spark-Monitoring related libraries"
#Copy all the spark monitoring library to the destination directory
dbfs cp --overwrite --recursive ../Azure/databricks-monitoring/ dbfs:/databricks/spark-monitoring/
#List all the Spark monitoring library
dbfs ls dbfs:/databricks/spark-monitoring/
#Show the content of Spark-monitoring script
dbfs cat dbfs:/databricks/spark-monitoring/spark-monitoring.sh
Write-Log "INFO" "Complete Copy Spark-Monitoring related libraries"

# Cleanup Enivronment Parameters
[Environment]::SetEnvironmentVariable('DATABRICKS_HOST',$null)
[Environment]::SetEnvironmentVariable('DATABRICKS_TOKEN',$null)

Write-Log "INFO" "Configure Log Analytics for Databricks Successfully!"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }