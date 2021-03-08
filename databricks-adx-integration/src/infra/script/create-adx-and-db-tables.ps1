<#
[Microsoft Kusto Lab Project]
Azure Data Explorer resource provisioning
1. Including the provisioning the following resources:
   Azure Data Explorer:
   Multi-Tenant Databases
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

#Set Environement Variable for creating ADX Tables
Function Set-Environment-Variables {
    [CmdletBinding()]
    Param(
    [Parameter(Mandatory=$True)]
    [Object]
    $configObj,
    [Parameter(Mandatory=$True)]
    [ValidateSet("create","delete")]
    [String]
    $action
    )
    if($action.ToLower().Equals("create")){
        $clusterName = (Get-Resource-Prefix $config.ResourceGroupName)+$configObj.ADX.ClusterName
        [Environment]::SetEnvironmentVariable('RETENTION_DAYS',$configObj.ADX.TableRetentionDays)
        [Environment]::SetEnvironmentVariable('CLIENT_ID',$configObj.DeployClientId)
        [Environment]::SetEnvironmentVariable('CLIENT_SECRET',$configObj.DeploySecret)
        [Environment]::SetEnvironmentVariable('TENANT_ID',$configObj.AzureTenantId)
        [Environment]::SetEnvironmentVariable('REGION',$configObj.Location)
        [Environment]::SetEnvironmentVariable('CLUSTER_NAME',$clusterName)
        [Environment]::SetEnvironmentVariable('SUBSCRIPTION_ID',$configObj.AzureSubscriptionId)
        [Environment]::SetEnvironmentVariable('RESOURCE_GROUP',$configObj.ResourceGroupName)
    }
    elseif ($action.ToLower().Equals("delete")){
        [Environment]::SetEnvironmentVariable('RETENTION_DAYS',$null)
        [Environment]::SetEnvironmentVariable('CLIENT_ID',$null)
        [Environment]::SetEnvironmentVariable('CLIENT_SECRET',$null)
        [Environment]::SetEnvironmentVariable('TENANT_ID',$null)
        [Environment]::SetEnvironmentVariable('REGION',$null)
        [Environment]::SetEnvironmentVariable('CLUSTER_NAME',$null)
        [Environment]::SetEnvironmentVariable('SUBSCRIPTION_ID',$null)
        [Environment]::SetEnvironmentVariable('RESOURCE_GROUP',$null)
    }
}

Function Get-Zones-Array {
    [CmdletBinding()]
    Param(
    [Parameter(Mandatory=$True)]
    [Object]
    $zones
    )    
    $zone_str = ""
    $zones | ForEach-Object {
        $zone = $_   
        $zone_str = $zone_str + '\"'+$zone+'\",'
    }
    $remove_last_char_zones = $zone_str.Substring(0, $zone_str.Length-1)
    $zonesAry = '['+$remove_last_char_zones+']'
    return $zonesAry
}

Write-Log "INFO"  "====  Kusto Lab - Module2 Create ADX services, Databases, Tables===="
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
Write-Log "INFO" "Preparing ADX Parameters....."
$clusterName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.ADX.ClusterName
Write-Log "INFO" "clusterName: $clusterName"
$zonesAry = Get-Zones-Array $config.ADX.AvaliabilityZones

$adx_parameters_strParamValues = @{
    ClusterName=$clusterName
    Location=$config.Location
    ClusterSkuName=$config.ADX.ClusterSkuName
    ClusterSkuTier=$config.ADX.ClusterSkuTier
     
}
$adx_parameters_objParamValues = @{
    ClusterSkuCapacity=$config.ADX.ClusterSkuCapacity
    AvaliabilityZones=$zonesAry   
}
$adx_parameters =  ConvertTo-ARM-Parameters-JSON $adx_parameters_strParamValues $adx_parameters_objParamValues

Write-Log "INFO" "Before Deploy, adx_parameters = $adx_parameters"
Write-Log "INFO" "Before Deploy clustername: $clusterName"

#Start Resource Deployement
Publish-Azure-Deployment $clusterName $config.ResourceGroupName $config.ADX.ADXTemplatePath $adx_parameters "ADXDeployment"

#Start Creating Multi-Tenant DBs
#Set up Environment Variables
Set-Environment-Variables $config "create"

$dbProvisionToolPath = "../../code/tools/ADXProvisionTool/"

Write-Log "INFO" "Install requirements for adx database creation" 
#Install Required Packages
pip install -r (Join-Path -Path $dbProvisionToolPath -ChildPath "requirements.txt") --user

#database num
Write-Log "INFO" "Start to create ADX database " 
Write-Log "INFO" "Start to create $($config.ADX.DatabaseNum) ADX databases"
#Create ADX DB
python (Join-Path -Path $dbProvisionToolPath -ChildPath "create_dataexplorer_database.py") createDatabase -s (Join-Path -Path $dbProvisionToolPath -ChildPath "FieldList") -c $config.ADX.DatabaseNum
#Create ADX Tables
Write-Log "INFO" "Start to create $($config.ADX.DatabaseNum) tables"
python (Join-Path -Path $dbProvisionToolPath -ChildPath "create_dataexplorer_database.py") createTableofDatabase -s (Join-Path -Path $dbProvisionToolPath -ChildPath "FieldList") -c $config.ADX.DatabaseNum

#Remove Environment Variables
Set-Environment-Variables $config "delete"

Write-Log "INFO" "Create $($config.ADX.DatabaseNum) ADX databases successfully! "

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
 }