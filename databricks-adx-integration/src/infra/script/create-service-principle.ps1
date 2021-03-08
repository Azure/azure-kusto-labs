
# This code will generate Service Principle 


Write-Host "This code will get will generate Service Principle  and assing it to Contributor role of the susbcription "
Write-Host "You need to log-in Azure CLI with the account that is authorized to create service principle in your Azure AD tenant."
Write-Host "=============================================================================================="

$ErrorActionPreference = 'Stop'
# setup temporary profile path for the alternative user
$altIdProfilePath = Join-Path ([io.path]::GetTempPath()) '.azure-altId'

try {
    # check whether already logged-in
    $currentToken = $(az account get-access-token) | ConvertFrom-Json
	
    if ([datetime]$currentToken.expiresOn -le [datetime]::Now) {
        throw
    }
	
	Write-Host "You already login"
}
catch {
    Write-Host 'You need to login'
    az login | Out-Null
    if ($LASTEXITCODE -ne 0) { exit 1 }
}


Write-Host "You are logged-in (default credential)"
Write-Host "Output from 'az account show':"
az account show --query user

#Input Service Principle URL
$servicePrincipleName = Read-Host -Prompt 'Input the Service Principle name (default: KustoLab-Databirck-ADX-SPId)'
if ([string]::IsNullOrWhiteSpace($servicePrincipleName))
{
    $servicePrincipleName = 'KustoLab-Databirck-ADX-SPId'
}



# create a test SPN
Write-Host "`nCreating temporary SPN..."
$newUser = $(az ad sp create-for-rbac -n $servicePrincipleName --skip-assignment) | ConvertFrom-Json

Write-Host "Start to Assign Service Principle to Contributor role of Resource Group.."


$subscription=$(az account show --query "id" -otsv)
Write-Host "Subsriptoin ID $subscription"

az role assignment create --assignee  $newUser.appId --scope "/subscriptions/$($subscription)" --role "Contributor"


Write-Host "Created Service Principle Id (appId): $($newUser.appId)"
Write-Host "Service Principle Password: $($newUser.password)" 
Write-Host "Successfully assigned Service Principle $($newUser.appId) to Contributor role"
Write-Host "Please save the Service Principle Id and Password in somewhere you can access later "
