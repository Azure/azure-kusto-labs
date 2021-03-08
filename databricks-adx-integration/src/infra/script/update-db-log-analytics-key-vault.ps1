<#
[Microsoft Kusto Lab Project]
 Get and Set Key Valut Values for Databircks Log Analytics Connector
#>

#Reference Utility Function Scripts
. ".\util\common-util.ps1"
. ".\util\azure-util.ps1"

Write-Log "INFO"  "====   Kusto Lab - Databricks ADX Integration - Module7 : Step 2-2         ===="
Write-Log "INFO"  "====   Get and Set Key Valut Values for Databircks Log Analytics Connector ====" 
Write-Log "INFO"  "===============================================================================" 

#Get Global Config
$config = Get-Content .\config\provision-config.json | ConvertFrom-Json

Write-Log "INFO" "Connect to Azure using Service Principal" 
# Connect to Azure
Connect-Azure $config

$resourceName = (Get-Resource-Prefix $config.ResourceGroupName)+$config.KeyVault.DatabricksKeyVaultName
Write-Log "INFO" "Resource Name: $($resourceName)"


$workspaceId=(az monitor log-analytics workspace list --resource-group $config.ResourceGroupName --subscription $config.AzureSubscriptionId) | ConvertFrom-Json| where { $_.name -eq (Get-Resource-Prefix $config.ResourceGroupName)+$config.LogAnalytics.WorkspaceName }
$workspaceId=$workspaceId.customerId
#$workspaceId=(az monitor log-analytics workspace list --resource-group $config.ResourceGroupName) | ConvertFrom-Json| where { $_.name -eq (Get-Resource-Prefix $config.ResourceGroupName)+$config.LogAnalytics.WorkspaceName }

$workspaceName=(Get-Resource-Prefix $config.ResourceGroupName)+$config.LogAnalytics.WorkspaceName
Write-Log "INFO"  "LogAnalytics Workspace Name $($workspaceName)" 

$workspaceKey=(az monitor log-analytics workspace get-shared-keys --resource-group $config.ResourceGroupName --subscription $config.AzureSubscriptionId --workspace-name $workspaceName) | ConvertFrom-Json
$workspaceKey=$workspaceKey.primarySharedKey
Write-Log "INFO"  "workspaceKey= ID : $($workspaceKey)" 

$secretPairs = '{'+ 
  '\"secretPairs\":['+
    '{\"key\": \"'+($config.LogAnalytics.SecretScopeKeyWorkspaceId)+'\",\"value\": \"'+$workspaceId+'\"},'+
    '{\"key\": \"'+($config.LogAnalytics.SecretScopeKeyWorkspaceKey)+'\",\"value\": \"'+$workspaceKey+'\"}'+
  ']'+
'}'

$keyvault_secret_parameters = '{'+
     '\"KeyVaultName\": {\"value\": \"'+$resourceName+'\"},'+
     '\"Secrets\": {\"value\": '+$secretPairs+'}'+
'}'

Publish-Azure-Deployment $resourceName $config.ResourceGroupName $config.KeyVault.KeyVaultSecretTemplatePath $keyvault_secret_parameters "Databrick-KeyVaultSecretDeployment" 

# Logout from Azure when "AutoAzLogout" is set to true
if($config.AutoAzLogout -eq $true){
    Write-Log "INFO" "Logout from Azure"
    az logout
}