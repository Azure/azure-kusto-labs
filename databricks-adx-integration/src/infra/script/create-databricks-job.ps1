<#
[Microsoft Kusto Lab Project] Creat Databrick Structured Streaming Jobs

Environment Pre-requests: 
    1. Databricks CLI intalled
    2. Azure CLI with Databricks Extension installed
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module1 : Step 3 ===="
Write-Log "INFO"  "====                Create Databricks Jobs                      ====" 
Write-Log "INFO"  "====================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

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

# Extract Azure Access Token for Databricks
$azToken=$(az account get-access-token --resource $DATABRICKS_MANAGEMENT_PORTAL_URL ) | ConvertFrom-Json
$azToken=$azToken.accessToken
Write-Log "INFO" "Got Azure Access Token for Databricks"

# Extract Databricks Workspace URL
$workspaceUrl=$(az databricks workspace list --resource-group  $config.ResourceGroupName  --query "[?name == '$db_service'].workspaceUrl|[0]")
$workspaceUrl=$workspaceUrl -replace '"',''
Write-Log "INFO" "Databricks WorkSpacke URL: $($workspaceUrl)" 

#Create Queue Name List String 
$queueNameList = ""
foreach($number in 0..($config.EventGrid.LandingEventQueueCount-1))
{
    $queueNameList += "$($config.EventGrid.LandingEventQueueName)$number,"
}
$queueNameList=$queueNameList.Substring(0,($queueNameList.Length-1))
Write-Log "INFO" "Landing Stroage Queues: $($queueNameList)" 

# SET Job Parameters
$ParamValues = @{
    job_name_param= $config.DatabricksJob.DatabricksJobName
    spark_version_param =$config.DatabricksJob.DatabricksSparkVersion 
    node_type_id_param =$config.DatabricksJob.DatabricksNodeSpec
    secret_scope_param =$config.Databricks.DBSSecretScopeName
    landing_sa_param =(Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.LandingDatalakeName
    ingestion_sa_param =(Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.IngestionDatalakeName
    container_param =$config.Storage.FileSystemName
    root_folder_param =$config.Storage.FileSystemNameRootFolder
    target_folder_param =$config.Storage.AzureStorageTargetFolder
    check_point_folder_param =$config.DatabricksJob.AzureStorageCheckPointFolder
    bad_record_folder_param =$config.Storage.LandingBadRecordFolder
    queue_name_list_param =$queueNameList
    min_workers_param =$config.DatabricksJob.DatabricksMinWorkersCount
    max_workers_param =$config.DatabricksJob.DatabricksMaxWorkersCount
    log_secret_scope_log_wsid_param= $config.LogAnalytics.SecretScopeKeyWorkspaceId
    log_secret_scope_log_wskey_param=$config.LogAnalytics.SecretScopeKeyWorkspaceKey
    log_secret_scope_param=$config.LogAnalytics.SecretScope
}

#Set Environment Variable for Databricks
[Environment]::SetEnvironmentVariable('DATABRICKS_HOST',"https://"+$workspaceUrl)
[Environment]::SetEnvironmentVariable('DATABRICKS_TOKEN',$databrickToken)

# Create Job Parameters Config Files
$scopeNameCount = (databricks secrets list-scopes| select-string -pattern $config.LogAnalytics.SecretScope).length
Write-Log "INFO" "Find $($scopeNameCount) Databricks secret scope named $($config.LogAnalytics.SecretScope)"
if ($scopeNameCount -eq 1){
    $JobConfigContent = Get-Content -Path ../Azure/databricks/JobSpec.cfg.enablelog.template -Raw
    Write-Log "INFO" "Found Databricks Secret Scope $($config.LogAnalytics.SecretScope), deploy Databrick Job and enable Log Analytics"
} else {
    Write-Log "INFO" "Didn't find Databricks Secret Scope $($config.LogAnalytics.SecretScope), deploy Databrick Job without enable Log Analytics"
    $JobConfigContent = Get-Content -Path ../Azure/databricks/JobSpec.cfg.template -Raw 
}

$paramValues.keys | ForEach-Object{
    $JobConfigContent=$JobConfigContent -replace $_, $paramValues[$_]
}
Set-Content -Path  $Config.DatabricksJob.DatabricksJobParamPath -Value $JobConfigContent
Write-Log "INFO" "Before Deploy, Databricks Jobs Parameters = $JobConfigContent"


$jobId=databricks jobs create --json-file $Config.DatabricksJob.DatabricksJobParamPath  | ConvertFrom-Json

# Cleanup Enivronment Parameters
[Environment]::SetEnvironmentVariable('DATABRICKS_HOST',$null)
[Environment]::SetEnvironmentVariable('DATABRICKS_TOKEN',$null)


if ($jobId.job_id  -match "[0-9]+"){
    Write-Log "INFO" "Databricks Job Deployed: $($jobId.job_id)" 
    Write-Log "INFO" "Deploy $resourceName successfully!"  
}
else{
    Write-Log "ERROR" "$workspaceUrl Job doesn't create successfully, the deployment job will be terminated...."
    Write-Log "ERROR" "Job Create Result $jobId."
    throw "Illigal Job ID "
    return
}
# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }