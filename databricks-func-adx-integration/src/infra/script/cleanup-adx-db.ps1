<#
==============          [Microsoft Kusto Lab Project]          ================
=   This script will clean(drop) all the data in Azure Data Explorer Tables   = 
===============================================================================
#>

#TODO: Add Warning message about data will be deleted and let user choose

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module4 : Step 1 ===="
Write-Log "INFO"  "====                   Clean Up ADX Tables                      ====" 
Write-Log "INFO"  "====================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Set up Environment Variables for ADX Python SDK
Set-ADX-Python-SDK-Environment-Variables $config

Set-Variable ADX_TOOLS_PATH -option Constant -value  "..\..\code\tools\LoadTest\utils\"

Write-Log "INFO" "Install requiremens for Kusto Python SDK" 
#Install Required Packages
pip install -r (Join-Path -Path $ADX_TOOLS_PATH -ChildPath "requirements.txt") --user

#Cleanup ADX DB
Write-Log "INFO" "Start to cleanup tables " 
Write-Log "INFO" "Start to create $($config.ADX.DatabaseNum) databases"

python (Join-Path -Path $ADX_TOOLS_PATH -ChildPath "cleanup_adx_all_db_records.py") 
#Clean up Environment Variables for ADX Python SDK
Set-ADX-Python-SDK-Environment-Variables $null 

