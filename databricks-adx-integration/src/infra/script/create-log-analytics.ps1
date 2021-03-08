<#
[Microsoft Kusto Lab Project] Creat Log Analytics Workspace
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module7 : Step 1 ===="
Write-Log "INFO"  "====               Create Log Analytics Workspac                ====" 
Write-Log "INFO"  "====================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Start Log Analytics deployment
Write-Log "INFO" "Preparing Log Analytics Parameters....."
$resourceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.LogAnalytics.WorkspaceName
Write-Log "INFO" $resourceName

$la_strParamValues = @{
   WorkspaceName=$resourceName
   Location=$config.Location
   ServiceTier=$config.LogAnalytics.ServiceTier
}
$la_numParamValues = @{
}
$la_parameters = ConvertTo-ARM-Parameters-JSON $la_strParamValues $la_numParamValues  


Write-Log "INFO" "Before Deploy, la_parameters = $la_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.LogAnalytics.ARMTemplatePath $la_parameters "LogAnalyticsDeployment"

Write-Log "INFO" "Create Log Analytics Successfully!"

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
   Write-Log "INFO" "Logout from Azure"
   az logout
}