# This code will get Azure Subscription ID, Tenant ID , Service Principle Client ID and Object ID

Write-Host "This code will get Azure Subscription ID, Tenant ID , Service Principle Client ID and Object ID"
Write-Host "You need to log-in Azure CLI using your Service Principle, if you don't have one you can use create-service-principle.ps1 script to create one."
Write-Host "=============================================================================================="
$ErrorActionPreference = 'Stop'

#Login Service Principle 
$appId = Read-Host -Prompt 'Input your appId (Service Principle ID)'
$appPwd = Read-Host -Prompt 'Input your Service Principle Password'
$tenantId=($azSubscriptionInfo= az account show | ConvertFrom-Json).tenantId
az login --service-principal -u $appId  -p $appPwd  --tenant $tenantId  --allow-no-subscriptions


# setup temporary profile path for the alternative user

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

Write-Host "You logged-in Service Principle $($appId) in tenant $($tenantId)"

$azSubscriptionInfo= az account show | ConvertFrom-Json
$spObjectId=(az ad sp show --id $azSubscriptionInfo.user.name --query objectId) -replace '"',''

Write-Host "** Azure Subcription Name is $($azSubscriptionInfo.name)"
Write-Host "** Azure Subcription ID is $($azSubscriptionInfo.id)"
Write-Host "** Azure tenantId ID is $($azSubscriptionInfo.tenantId)"
Write-Host "** Azure User Name(Application/Client ID) is  $($azSubscriptionInfo.user.name)"
Write-Host "** Azure Object ID is  $($spObjectId)"

