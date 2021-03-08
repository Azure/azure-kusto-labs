<#
==============          [Microsoft Kusto Lab Project]          ================
=      This script will change the "IS_DUPLICATE_CHECK" setting of            =
=      ADX Ingetion Functions                                                 = 
===============================================================================
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "==== Kusto Lab - Databricks ADX Integration - Module6 : Step 4            ===="
Write-Log "INFO"  "====   change the IS_DUPLICATE_CHECK setting of  ADX Ingetion Functions   ====" 
Write-Log "INFO"  "==============================================================================" 


#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

$functionName=(Get-Resource-Prefix $config.ResourceGroupName)+$config.Functions.IngestionFunction.FunctionName+"0"
$appSettings="""IS_DUPLICATE_CHECK=TRUE"" ""STORAGE_TABLE_ACCOUNT=$((Get-Resource-Prefix $config.ResourceGroupName) +$config.Storage.TableStorageAccountName)"""
Write-Log "INFO" "Updata Functions $($functionName) with settings $($appSettings)"

$result=(az functionapp config appsettings set --name $functionName  --resource-group $config.ResourceGroupName --settings "IS_DUPLICATE_CHECK=TRUE")| ConvertFrom-Json
$id_du_check=$result | where { $_.name -eq "IS_DUPLICATE_CHECK" }
Write-Log "INFO" "IS_DUPLICATE_CHECK is now : $($id_du_check.value) "


$result=(az functionapp config appsettings set --name $functionName  --resource-group $config.ResourceGroupName --settings "STORAGE_TABLE_ACCOUNT=$((Get-Resource-Prefix $config.ResourceGroupName) +$config.Storage.TableStorageAccountName)")| ConvertFrom-Json
$storageTable=$result | where { $_.name -eq "STORAGE_TABLE_ACCOUNT" }
Write-Log "INFO" "STORAGE_TABLE_ACCOUNT is now : $($storageTable.value)"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }