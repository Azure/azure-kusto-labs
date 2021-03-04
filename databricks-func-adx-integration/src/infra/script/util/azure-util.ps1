<#
[Microsoft Kusto Lab Project]
Azure Environment Provisioing Utility Function
1. Including the following functions:
   Connect-Azure: Azure Login
   Publish-Azure-Deployment: Azure Deployment using ARM template
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
Function Connect-Azure {
    [CmdletBinding()]
    Param(
        [Parameter(Mandatory=$True)]
        $config
    )
    # Connect to Azure using Service Principal
    az login --service-principal -u $config.DeployClientId -p $config.DeploySecret --tenant $config.AzureTenantId
    az account set --subscription $config.AzureSubscriptionId
    az account show
}

<#
.SYNOPSIS
    This Function is untility tool to deploy azure service by arm template

.PARAMETER deploymentName
    The parameter deploymentName is used to define the deployment name

.PARAMETER armTemplateParameters
    The parameter armTemplateParameters is used to define the parameters in ARM template

.PARAMETER armTemplateFilePath
    The parameter armTemplateFilePath is used to define the ARM Template Path for specific azure service

.PARAMETER resourceName
    The parameter resourceName is used to define the coresponding azure service name

.PARAMETER resourceGroupName
    The parameter resourceGroupName is used to define the Azure Resource Group Name
#>
Function Publish-Azure-Deployment {
    [CmdletBinding()]
    Param(
    [Parameter(Mandatory=$True)]
    [String]
    $resourceName,

    [Parameter(Mandatory=$True)]
    [String]
    $resourceGroupName,

    [Parameter(Mandatory=$True)]
    [String]
    $armTemplateFilePath,

    [Parameter(Mandatory=$True)]
    [String]
    $armTemplateParameters,

    [Parameter(Mandatory=$False)]
    [String]
    $deploymentName
    )

    
    $result = az deployment group create --resource-group $resourceGroupName --template-file $armTemplateFilePath --parameters $armTemplateParameters --name $deploymentName | ConvertFrom-Json
    
    if(!$result)
    {
        Write-Log "ERROR" "Deploy resource: $resourceName in resource group: $resourceGroupName failed, the deployment script will be terminated.... `n"
    }
    else {
        Write-Log "INFO" "Deploy result: $result"
        Write-Log "INFO" "Deploy resource: $resourceName in resource group: $($result.resourceGroup) successfully `n "
    }
    return $result
}

<#
.SYNOPSIS
    This Function is to deploy function code under azure-kusto-labs\
    databricks-adx-integration\src\code\functions to the azure function service

.DESCRIPTION
Implementation Details:
    1 change to target function code file directory
    2 create a new Json file based on the json.template file for the function deployment
    3 updating the function.json file with the trigger name instance
    4 Using azure function core tools to publish function code to target resource

.PARAMETER path
    The parameter path is used to define the Function Folder Name under azure-kusto-labs\databricks-adx-integration\src\code\functions

.PARAMETER functionFolder
    The parameter functionFolder is used to define more concrete Function Folder under path\_app_\

.PARAMETER triggerQueueName
    The parameter triggerQueueName is used to define the function queue trigger name

.PARAMETER resourceName
    The parameter resourceName is used to define the coordinating azure function service name
#>
Function Publish-Azure-Function-Deployment {
    [CmdletBinding()]
    Param(
    [Parameter(Mandatory=$True)]
    [String]
    $path,

    [Parameter(Mandatory=$True)]
    [String]
    $functionFolder,

    [Parameter(Mandatory=$True)]
    [String]
    $triggerQueueName,

    [Parameter(Mandatory=$True)]
    [String]
    $resourceName
    )

    Set-Location ../../code/functions/$path/__app__
    Copy-Item ./$functionFolder/function.json.template ./$functionFolder/function.json
    (Get-Content -Path ./$functionFolder/function.json -Raw) -Replace '@TRIGGER_QUEUE_NAME', "$triggerQueueName" |
        Set-Content -Path ./$functionFolder/function.json
    $result = func azure functionapp publish $resourceName --python
    Set-Location ../../../../infra/script
    if(!$result)
    {
        Write-Log "ERROR" "Deploy function: $resourceName failed, the deployment script will be terminated.... `n"
    }
    else {
        Write-Log "INFO" "Deploy result: $result"
        Write-Log "INFO" "Deploy function: $resourceName successfully `n "
    }
    return $result

}


# Generate ARM Parameters JSON file based on two Hashtable parameters, firt Hashtable parameter ($strParameters) has string values, second Hashtable parameters has non-string values($nonStrParameters)
Function ConvertTo-ARM-Parameters-JSON {
    [CmdletBinding()]
    Param(
    [Parameter(Mandatory=$True)]
    [Hashtable]
    $strParameters,

    [Parameter(Mandatory=$False)]
    [Hashtable]
    $nonStrParameters
    )
    $armParameters = "{"

    #Add ARM String Parameters
    $strParameters.keys | ForEach-Object{
        $armParameters += '"'+$_+'": {"value": "'+$strParameters[$_]+'"},'
    }

    # Add Escape character
    $armParameters=$armParameters -replace '"','\"' 

    #Add ARM Numerical Parameters
    if ($nonStrParameters -ne $null) {
        $nonStrParameters.keys | ForEach-Object{
        $armParameters += '\"'+$_+'\": {\"value\": '+$nonStrParameters[$_]+'},'
        }
    }

    $armParameters =$armParameters.Substring(0,$armParameters.Length-1)
    $armParameters +="}"

    return $armParameters
}

#Extract Resource Prefix by converting to lower cases and extract only the first word characters part ([a-zA-Z0-9]) 
Function Get-Resource-Prefix {
    [CmdletBinding()]
    Param(
    [Parameter(Mandatory=$True)]
    [String]
    $strName
    )
    # Max Prefix Length
    $max_prefix_length=8

    #Extract Resource Name Prefix (Lower Case Letter)
    if($strName -match  "[a-zA-Z0-9]+") { 
        $resourcePrefix= $Matches[0].ToLower() 
    } else { 
        throw "Couldn't Extrac lligal Resource Prefix, Please Make Sure Resource Group Name Start With Alphabet Letters" 
    }

    # Ensure Prefix's max length is within $max_prefix_length
    $resourcePrefix=$resourcePrefix.subString(0, [System.Math]::Min($max_prefix_length, $resourcePrefix.Length))  

    return $resourcePrefix
}

Function Set-EventGrid-Filter {
    [CmdletBinding()]
    Param(
    [Parameter(Mandatory=$True)]
    [Object]
    $jsonObj
    )

    $filter = ""
    $jsonObj | ForEach-Object {
        $key = $_.key
        $operatorType = $_.operatorType
        $value = ""       
        $_.values | ForEach-Object {
            $values = $_
            $value = $value + '\"'+$values+'\",'
        }
        $remove_last_char_values = $value.Substring(0,$value.Length-1)
        $filter = $filter + '{\"key\":\"'+$key+'\",\"operatorType\": \"'+$operatorType+'\",\"values\": ['+$remove_last_char_values+']},'
    }
    $remove_last_char_filter = $filter.Substring(0,$filter.Length-1)
    $newFilterAry = '['+$remove_last_char_filter+']'
    
    return $newFilterAry
}
