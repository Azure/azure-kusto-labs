<#
[Microsoft Kusto Lab Project]
Basic infra resource provisioning
1. Including the provisioning the following resources:
   Storage:
   Landing Datalake
   Ingestion Datalake
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module0 : Step 1 ===="
Write-Log "INFO"  "====                    Create Datalakes                        ====" 
Write-Log "INFO"  "====================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Create Resouce Group First
Write-Log "INFO" "Creating/Assign Resource Group for Deployment" 
az group create -l $config.Location -n $config.ResourceGroupName


#Start storage deployment
Write-Log "INFO" "Preparing Landing Storage Parameters....."
$resourceName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.LandingDatalakeName


$landing_storage_strParamValues = @{
    DatalakeName=$resourceName
    Location=$config.Location
    StorageSku=$config.Storage.StorageSku
    AccessTier=$config.Storage.AccessTier
    FileSystemName=$config.Storage.FileSystemName
    ErrorHandleFileSystemName=$config.Storage.LandingErrorHandleFileSystemName
    FileSystemNameRootFolder=$config.Storage.FileSystemNameRootFolder
}
$landing_storage_numParamValues = @{
    TelemetryLogfileRetentionDays=$config.Storage.TelemetryLogfileRetentionDays
}
$landing_storage_parameters =  ConvertTo-ARM-Parameters-JSON $landing_storage_strParamValues $landing_storage_numParamValues  

Write-Log "INFO" "Before Deploy, landing_storage_parameters = $landing_storage_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.Storage.DatalakeTemplatePath $landing_storage_parameters "LandingStorageDeployment"

Write-Log "INFO" "Preparing Ingestion Storage Parameters....."
$resourceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.IngestionDatalakeName

$ingestion_storage_strParamValues = @{
    DatalakeName=$resourceName
    Location=$config.Location
    StorageSku=$config.Storage.StorageSku
    AccessTier=$config.Storage.AccessTier
    FileSystemName=$config.Storage.FileSystemName
    ErrorHandleFileSystemName=$config.Storage.IngestionRetryEndInFailContainerName
    FileSystemNameRootFolder=$config.Storage.FileSystemNameRootFolder
}
$ingestion_storage_numParamValues = @{
    TelemetryLogfileRetentionDays=$config.Storage.TelemetryLogfileRetentionDays
}
$ingestion_storage_parameters = ConvertTo-ARM-Parameters-JSON $ingestion_storage_strParamValues $ingestion_storage_numParamValues  

Write-Log "INFO" "Before Deploy, ingestion_storage_parameters = $ingestion_storage_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.Storage.DatalakeTemplatePath $ingestion_storage_parameters "IngestionStorageDeployment"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }