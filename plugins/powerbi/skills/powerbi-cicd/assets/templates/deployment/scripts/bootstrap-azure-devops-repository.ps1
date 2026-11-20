[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)][string]$ConfigPath,
    [Parameter(Mandatory)][string]$EvidencePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$config = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
if (-not $config.azure_devops.organization -or -not $config.azure_devops.project -or -not $config.azure_devops.repository) {
    throw 'The approved Azure DevOps organization, project, and repository are required.'
}
if ($config.repository.dev_branch -ne 'dev' -or $config.repository.prod_branch -ne 'main') {
    throw 'The Power BI lifecycle requires dev and main promotion branches.'
}

# This helper is intentionally configuration-led.  Its caller chooses whether
# to invoke az; this template never constructs a repository URL or stores a
# credential.  The evidence is the reviewed input to the later gated setup.
$record = [ordered]@{
    captured_at = (Get-Date).ToUniversalTime().ToString('o')
    action = 'repository-bootstrap-plan'
    repository = [ordered]@{
        organization = $config.azure_devops.organization
        project = $config.azure_devops.project
        repository = $config.azure_devops.repository
        dev_branch = $config.repository.dev_branch
        prod_branch = $config.repository.prod_branch
    }
    proposed_actions = @('reconcile configured repository branches and policies through developer-authenticated az')
    external_writes = $false
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $EvidencePath) | Out-Null
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $EvidencePath -Encoding utf8
