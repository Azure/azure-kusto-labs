<#
[Microsoft Kusto Lab Project]
Azure Environment Provisioing Common Utility Function
1. Including the following functions:
   Write-Log: Log Message
   Set-ADX-Python-SDK-Environment-Variables: Set/Clean environment variables 

#>

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json
$appName = $config.AppName

<#
.SYNOPSIS
    This Function is to provide Log function During Running the Powershell Script

.PARAMETER Level
    The parameter Level is logging level for different kind of infomration, Non-Mandatory parameter, default is [INFO]
    [DEBUG]: Debug information
    [INFO]: Information
    [WARN]: Warning message
    [ERROR]: Error message, if you use this category, it will stop the cmd
    [FATAL]: Fatal message, if you use this category, it will stop the cmd

.PARAMETER Message
    The parameter Message is message you want to print out, Mandatory parameter

.PARAMETER logfile
    The parameter logfile is logfile path if you want to output the log to an file, Non-Mandatory parameter
#>
Function Write-Log {
    [CmdletBinding()]
    Param(
    [Parameter(Mandatory=$False)]
    [ValidateSet("INFO","WARN","ERROR","FATAL","DEBUG")]
    [String]
    $Level = "INFO",

    [Parameter(Mandatory=$True)]
    [string]
    $Message,

    [Parameter(Mandatory=$False)]
    [string]
    $logfile
    )

    $Stamp = (Get-Date).toString("yyyy/MM/dd HH:mm:ss")
    $Line = "[$appName] [$Stamp] [$Level] $Message"
    If($logfile) {
        Add-Content $logfile -Value $Line
        if( ($Level.Equals("ERROR")) -or ($Level.Equals("FATAL")) )
        {
            Write-Error -Message $Line -ErrorAction Stop
        }
    }
    Else {
        if( ($Level.Equals("ERROR")) -or ($Level.Equals("FATAL")) )
        {
            Write-Error -Message $Line -ErrorAction Stop
        }
        else{
            Write-Host $Line
        }
    }
}

# Set environment variables for ADX Python API if $configObj is provided. 
# Cleanup environment variables if $configObjec is $null
Function Set-ADX-Python-SDK-Environment-Variables {
    [CmdletBinding()]
    Param(
    [Parameter(Mandatory=$false)]
    [Object]
    $configObj
    )
    If($configObj){
        $clusterName = (Get-Resource-Prefix $configObj.ResourceGroupName)+$configObj.ADX.ClusterName
        [Environment]::SetEnvironmentVariable("RETENTION_DAYS",$configObj.ADX.TableRetentionDays)
        [Environment]::SetEnvironmentVariable("CLIENT_ID",$configObj.DeployClientId)
        [Environment]::SetEnvironmentVariable("CLIENT_SECRET",$configObj.DeploySecret)
        [Environment]::SetEnvironmentVariable("TENANT_ID",$configObj.AzureTenantId)
        [Environment]::SetEnvironmentVariable("REGION",$configObj.Location)
        [Environment]::SetEnvironmentVariable("CLUSTER_NAME",$clusterName)
        [Environment]::SetEnvironmentVariable("SUBSCRIPTION_ID",$configObj.AzureSubscriptionId)
        [Environment]::SetEnvironmentVariable("RESOURCE_GROUP",$configObj.ResourceGroupName)
    }
    else 
    {
        $clusterName = ""
        [Environment]::SetEnvironmentVariable("RETENTION_DAYS","")
        [Environment]::SetEnvironmentVariable("CLIENT_ID","")
        [Environment]::SetEnvironmentVariable("CLIENT_SECRET","")
        [Environment]::SetEnvironmentVariable("TENANT_ID","")
        [Environment]::SetEnvironmentVariable("REGION","")
        [Environment]::SetEnvironmentVariable("CLUSTER_NAME","")
        [Environment]::SetEnvironmentVariable("SUBSCRIPTION_ID","")
        [Environment]::SetEnvironmentVariable("RESOURCE_GROUP","")
    }
}



