<#
==============      [Microsoft Kusto Lab Project]       ================
=    This script will upload sample telemtry data to Azure Data Lake   = 
========================================================================
#>


#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"


Write-Log "INFO"  "==== Kusto Lab - Databricks ADX Integration - Module4 : Step 2 ===="
Write-Log "INFO"  "====                Ingest Telemetry  Data                     ====" 
Write-Log "INFO"  "===================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

Set-Variable TELEMTRY_DATA_GENERATOR_TOOL -option Constant -value  "..\..\code\tools\FakeDataGenerator\"

Write-Log "INFO" "Install requiremens for Telemtry Data Generator Tool Python SDK" 
#Install Required Packages
pip install -r (Join-Path -Path $TELEMTRY_DATA_GENERATOR_TOOL -ChildPath "requirements.txt") --user

#Get Landing DataLake Account Name 
Write-Log "INFO" "Start to ingest telemtry data " 
$landingAccountName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.LandingDatalakeName

#Get Landing  DataLake Access Key
Write-Log "INFO" $landingAccountName
$key=$(az storage account keys list -g $config.ResourceGroupName -n $landingAccountName --query [0].value -o tsv)

#Generate telemetry data and upload to landing Azure data lake
# The generated telemetry names the destinations Module 2 provisioned, so the company
# ids and types it emits stay within the set the ingestion function serves.
[Environment]::SetEnvironmentVariable('NUMBER_OF_COMPANIES',$config.ADX.DatabaseNum)
[Environment]::SetEnvironmentVariable('DATABASE_NAME_FORMAT',$config.ADX.DatabaseNameFormat)
[Environment]::SetEnvironmentVariable('TABLE_LIST_STR',$config.ADX.TableList)
Write-Log "INFO" "Run fake_data_generator with parameters : -fc 1 -c 10 -i 3 -m 30 -ta $($landingAccountName) -tk $($key) -tc $($config.Storage.FileSystemName) -tf $($config.Storage.FileSystemNameRootFolder)"
python (Join-Path -Path $TELEMTRY_DATA_GENERATOR_TOOL -ChildPath "fake_data_generator.py") -fc 1 -c 10 -i 3 -m 30 -ta $landingAccountName -tk $key -tc $config.Storage.FileSystemName -tf $config.Storage.FileSystemNameRootFolder
[Environment]::SetEnvironmentVariable('NUMBER_OF_COMPANIES',$null)
[Environment]::SetEnvironmentVariable('DATABASE_NAME_FORMAT',$null)
[Environment]::SetEnvironmentVariable('TABLE_LIST_STR',$null)

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }
