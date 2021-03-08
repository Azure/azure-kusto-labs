<#
==============          [Microsoft Kusto Lab Project]          ================
=      This script will count the records in Azure Data Explorer Tables       = 
===============================================================================
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "==== Kusto Lab - Databricks ADX Integration - Module4 : Step 1,3 ===="
Write-Log "INFO"  "====            Count Records in ADX Tables                      ====" 
Write-Log "INFO"  "=====================================================================" 


#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json


#Set up Environment Variables
Set-ADX-Python-SDK-Environment-Variables $config
Set-Variable ADX_TOOLS_PATH -option Constant -value  "..\..\code\tools\LoadTest\utils\"

#Install Required Packages
Write-Log "INFO" "Install requiremens for Kusto Python SDK" 
pip install -r (Join-Path -Path $ADX_TOOLS_PATH -ChildPath "requirements.txt") --user


#Count Records in ADX Databases
Write-Log "INFO" "Start to count records in  tables " 
Write-Log "INFO" "Start to count records $($config.ADX.DatabaseNum) databases"

python (Join-Path -Path $ADX_TOOLS_PATH -ChildPath "count_adx_all_db_records.py") 
Set-ADX-Python-SDK-Environment-Variables $null 
