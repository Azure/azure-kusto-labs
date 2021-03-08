<#
[Microsoft Kusto Lab Project]
Monitor Module resource provisioning
1. Including the provisioning the following resources:
   a. Create Azure Monitor Dashboard for overall ingestion flow
#>
#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====  Kusto Lab - Databricks ADX Integration - Module7 : Step 4 ===="
Write-Log "INFO"  "====              Create Azure Dashboard                        ====" 
Write-Log "INFO"  "====================================================================" 

#Start to deploy Azure Resources
Write-Log "INFO" "Before deployment, please make sure you have installed the Powershell Core (version 6.x up) and latest Azure Cli"

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

#Start Action Group deployment
Write-Log "INFO" "Preparing Azure Dashabord Parameters....."
$mainDashboardName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.AzureMonitor.Dashboard.MainDashboardName
$landingDatalakeName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.LandingDatalakeName
$ingestionDatalakeName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Storage.IngestionDatalakeName
$ingestionFuncName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.Functions.IngestionFunction.FunctionName
$adxClusterName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.ADX.ClusterName

Write-Log "INFO" $mainDashboardName

$main_dashboard_parameters_str = @{
    DashboardName= $mainDashboardName
    LandingStorageAccountName = $landingDatalakeName 
    IngestionStorageAccountName = $ingestionDatalakeName
    IngestFuncName = $ingestionFuncName
    ADXClusterName = $adxClusterName
}
$main_dashboard_parameters_num = @{}

$main_dashboard_parameters = ConvertTo-ARM-Parameters-JSON $main_dashboard_parameters_str $main_dashboard_parameters_num 

Write-Log "INFO" "Before Deploy, main_dashboard_parameters = $main_dashboard_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $mainDashboardName $config.ResourceGroupName $config.AzureMonitor.Dashboard.MainDashboardTemplatePath $main_dashboard_parameters "MainDashboardDeployment"

#Start Databricks Dashboard deployment
Write-Log "INFO" "Preparing Databricks Dashboard Parameters....."
$dbsDashboardName =(Get-Resource-Prefix $config.ResourceGroupName)+$config.AzureMonitor.Dashboard.DBSDashboardName
$dbsLogAnalyticsName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.LogAnalytics.WorkspaceName

Write-Log "INFO" $dbsDashboardName

$dbs_dashboard_parameters_str = @{
    DashboardName= $dbsDashboardName
    DatabricksLogAnalyticsWorkspaceName = $dbsLogAnalyticsName
}
$dbs_dashboard_parameters_num = @{}

$dbs_dashboard_parameters = ConvertTo-ARM-Parameters-JSON $dbs_dashboard_parameters_str $dbs_dashboard_parameters_num 

Write-Log "INFO" "Before Deploy, dbs_dashboard_parameters = $dbs_dashboard_parameters"

#Start Resource Deployement
Publish-Azure-Deployment $dbsDashboardName $config.ResourceGroupName $config.AzureMonitor.Dashboard.DBSDashboardTemplatePath $dbs_dashboard_parameters "DBSDashboardDeployment"

Write-Log "INFO" "Deploy Azure Monitor Dashboard successfully!"    

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }