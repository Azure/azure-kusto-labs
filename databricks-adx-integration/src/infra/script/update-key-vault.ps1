<#
[Microsoft Kusto Lab Project]
Before Ingestion Function Module resource provisioning
1. Including the updating the following keyvault secret values:

#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module0 : Step 4 ===="
Write-Log "INFO"  "====               Get and Set Key Valut Values                 ====" 
Write-Log "INFO"  "====================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Start generate Storage SAS Token and Get Connection String then store into Key Vault
Write-Log "INFO" "Preparing Key Vault Secret Parameters....."
$resourceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.KeyVaultName
Write-Log "INFO" $resourceName

#Compose Storage Account Name
$landingAccountName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.LandingDatalakeName
$ingestionAccountName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.IngestionDatalakeName
#Get Landing Storage Connection String
$landingConnectionString = az storage account show-connection-string `
        -g $config.ResourceGroupName `
        -n $landingAccountName `
        --query connectionString `
        -o json


#Get Ingestion Storage Connection String
$ingestionConnectionString = az storage account show-connection-string `
        -g $config.ResourceGroupName `
        -n $ingestionAccountName `
        --query connectionString `
        -o json


#Set SAS Token Expiry Date, currently set expire date to 1 month later
$expiryDate = $(Get-Date).AddMonths(1).ToString("yyyy-MM-dd")
Write-Log "INFO" "SAS Token expiryDate = $expiryDate"

#Generate Landing Storage SAS Token
$landingSasToken = az storage account generate-sas `
        --permissions acdlpruw `
        --account-name $landingAccountName `
        --connection-string $landingConnectionString `
        --services bq `
        --resource-types sco `
        --expiry $expiryDate `
        -o json

Write-Log "INFO" "Got landingSasToken"


$ingestionSasToken = az storage account generate-sas `
        --permissions acdlpruw `
        --account-name $ingestionAccountName `
        --connection-string $ingestionConnectionString `
        --services bq `
        --resource-types sco `
        --expiry $expiryDate `
        -o json

Write-Log "INFO" "Got landingSasToken"

$secretPairs = '{'+ 
  '\"secretPairs\":['+
    '{\"key\": \"adxclientid\",\"value\": \"'+$config.DeployClientId+'\"},'+
    '{\"key\": \"adxclientsecret\",\"value\": \"'+$config.DeploySecret+'\"},'+
    '{\"key\": \"aadtenantid\",\"value\": \"'+$config.AzureTenantId+'\"},'+
    '{\"key\": \"ingestiontoken\",\"value\": \"'+$ingestionSasToken+'\"},'+
    '{\"key\": \"landingtoken\",\"value\": \"'+$landingSasToken+'\"},'+
    '{\"key\": \"landingconnectingstring\",\"value\": \"'+$landingConnectionString+'\"},'+
    '{\"key\": \"ingestionconnectingstring\", \"value\": \"'+$ingestionConnectionString+'\"}'+
  ']'+
'}'

$keyvault_secret_parameters = '{'+
     '\"KeyVaultName\": {\"value\": \"'+$resourceName+'\"},'+
     '\"Secrets\": {\"value\": '+$secretPairs+'}'+
'}'

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.KeyVault.KeyVaultSecretTemplatePath $keyvault_secret_parameters "KeyVaultSecretDeployment" 

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
}