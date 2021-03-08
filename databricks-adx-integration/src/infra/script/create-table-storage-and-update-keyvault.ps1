<#
[Microsoft Kusto Lab Project]
Module 6 resource provisioning
1. Including the provisioning the following resource:
   Storage:
   Table Storage for Logging Information
   Key Vault:
   Update Table Storage SAS token into Key Vault
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module 6 : Step 2 ===="
Write-Log "INFO"  "====        Create Table Storage & Update Key Vault              ====" 
Write-Log "INFO"  "=====================================================================" 

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
Write-Log "INFO" "Preparing Table Storage Parameters....."
$tableStorageName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.TableStorageAccountName

$logtable_storage_strParamValues = @{
    StorageName=$tableStorageName
    Location=$config.Location
    StorageSku=$config.Storage.TableStorageSku
    AccessTier=$config.Storage.AccessTier
}
$logtable_storage_numParamValues = @{}
$logtable_storage_parameters =  ConvertTo-ARM-Parameters-JSON $logtable_storage_strParamValues $logtable_storage_numParamValues  

Write-Log "INFO" "Before Deploy, logtable_storage_parameters = $logtable_storage_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $tableStorageName $config.ResourceGroupName $config.Storage.TableTemplatePath $logtable_storage_parameters "TableStorageDeployment"

#Start generating Storage SAS Token then store into Key Vault
Write-Log "INFO" "Preparing Key Vault Secret Parameters....."
$keyVaultName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.KeyVaultName
Write-Log "INFO" $keyVaultName

#Set SAS Token Expiry Date, currently set expire date to 1 month later
$expiryDate = $(Get-Date).AddMonths(1).ToString("yyyy-MM-dd")
Write-Log "INFO" "SAS Token expiryDate = $expiryDate"

#Get Table Storage Connection String
$tableStorageConnectionString = az storage account show-connection-string `
        -g $config.ResourceGroupName `
        -n $tableStorageName `
        --query connectionString `
        -o json

#Generate Table Storage SAS Token
$tableSasToken = az storage account generate-sas `
        --permissions acdlpruw `
        --account-name $tableStorageName `
        --connection-string $tableStorageConnectionString `
        --services t `
        --resource-types sco `
        --expiry $expiryDate `
        -o json

Write-Log "INFO" "Got tableSasToken"

$secretPairs = '{'+ 
  '\"secretPairs\":['+
    '{\"key\": \"logtabletoken\",\"value\": \"'+$tableSasToken+'\"},'+
  ']'+
'}'

$keyvault_secret_parameters = '{'+
     '\"KeyVaultName\": {\"value\": \"'+$keyVaultName+'\"},'+
     '\"Secrets\": {\"value\": '+$secretPairs+'}'+
'}'
Write-Log "INFO" "Got keyvault_secret_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $keyVaultName $config.ResourceGroupName $config.KeyVault.KeyVaultSecretTemplatePath $keyvault_secret_parameters "TableStorageKeyVaultSecretDeployment"

Write-Log "INFO" "Create Table Storage and Update Key Vault Successfully!"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
  Write-Log "INFO" "Logout from Azure"
  az logout
}