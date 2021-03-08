<#
[Microsoft Kusto Lab Project]
Azure Databricks resource provisioning
1. Including the provisioning the following resources:
   Azure Databricks Workspace
2. Update Storage Connection String to DBS Secret Scope
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module1 : Step 1 ===="
Write-Log "INFO"  "====                  Create Databricks                         ====" 
Write-Log "INFO"  "====================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Prepare databricks required packages
az extension add --name databricks
pip install databricks-cli

#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Create Resouce Group First
Write-Log "INFO" "Creating/Assign Resource Group for Deployment" 
az group create -l $config.Location -n $config.ResourceGroupName


#Start storage deployment
Write-Log "INFO" "Preparing Databricks Parameters....."
$resourceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Databricks.WorkspaceName
$dbsKeyVaultName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.DatabricksKeyVaultName
Write-Log "INFO" $resourceName

$dbs_strParamValues = @{
   WorkspaceName=$resourceName
   Location=$config.Location
   Sku=$config.Databricks.WorkspaceSku
   KeyVaultName=$dbsKeyVaultName
   AadObjectId=$config.DeployObjectId
}
$dbs_numParamValues = @{
}
$dbs_parameters = ConvertTo-ARM-Parameters-JSON $dbs_strParamValues $dbs_numParamValues  


Write-Log "INFO" "Before Deploy, dbs_parameters = $dbs_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.Databricks.DBSTemplatePath $dbs_parameters "DBSDeployment"
 

#Get Databricks Host URL using databricks-cli
$workspaceUrl= az databricks workspace list --resource-group $config.ResourceGroupName --query "[?name == '$resourceName'].workspaceUrl|[0]"
$workspaceUrl = $workspaceUrl -replace '\"', ''
Write-Log "INFO" "databricks workspaceUrl: $workspaceUrl"

#Get Databricks Token
$workspaceId=$(az databricks workspace list --resource-group $config.ResourceGroupName --query "[?name == '$resourceName'].id|[0]")
$workspaceid=$workspaceId -replace '"',''
Write-Log "INFO" "WorkspaceID is $workspaceId"

$globalDatabricksApplication = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"
$databricksManagementPortal = "https://management.core.windows.net/"
Write-Log "INFO" "globalDatabricksApplication: $globalDatabricksApplication, databricksManagementPortal: $databricksManagementPortal"

#Get Databricks access token from global Databricks Application
$databrickToken=($(az account get-access-token --resource $globalDatabricksApplication) | ConvertFrom-Json).accessToken
Write-Log "INFO" "Got Databricks Access Token"

#Get access token from Databricks management portal
$azToken=($(az account get-access-token --resource $databricksManagementPortal) | ConvertFrom-Json).accessToken
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
Write-Host $databricksUrl
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

#Use Databrick-Cli create secret scope and list the created secret scope
databricks secrets create-scope --scope $config.Databricks.DBSSecretScopeName --initial-manage-principal users
databricks secrets list-scopes

#Prepare Landing Storage Account Secret
$landingSA = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.LandingDatalakeName
$landingSAkey=$(az storage account keys list --account-name $landingSA --query "[?keyName == 'key1'].value | [0]")

#Prepare Ingestion Storage Account Secret
$ingestionSA = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.IngestionDatalakeName
$ingestionSAkey=$(az storage account keys list --account-name $ingestionSA --query "[?keyName == 'key1'].value | [0]")

#Get Connection String of Landing Storage Account
$landingConnectionString = az storage account show-connection-string `
        -g $config.ResourceGroupName `
        -n $landingSA `
        --query connectionString `
        -o tsv

Write-Log "INFO" "Start putting storage secrets into Databricks secret scope"
#Set storage secret into Databricks Secret Scope
databricks secrets put --scope $config.Databricks.DBSSecretScopeName --key source-files-secrets --string-value $landingSAkey
databricks secrets put --scope $config.Databricks.DBSSecretScopeName --key target-files-secrets --string-value $ingestionSAkey
databricks secrets put --scope $config.Databricks.DBSSecretScopeName --key cloud-files-connection-string --string-value $landingConnectionString
databricks secrets list --scope $config.Databricks.DBSSecretScopeName

# Cleanup Enivronment Parameters
[Environment]::SetEnvironmentVariable('DATABRICKS_HOST',$null)
[Environment]::SetEnvironmentVariable('DATABRICKS_TOKEN',$null)

Write-Log "INFO" "Create Databricks Successfully!"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
   Write-Log "INFO" "Logout from Azure"
   az logout
}