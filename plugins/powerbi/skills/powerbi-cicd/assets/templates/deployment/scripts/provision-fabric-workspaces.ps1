[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter(Mandatory)][string]$ConfigPath,
    [Parameter(Mandatory)][string]$EvidencePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$config = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
$required = @('TEST', 'PROD')
foreach ($name in $required) {
    if (-not $config.targets.$name.workspace_id -or $config.targets.$name.git_connected -ne $false) {
        throw "Configured $name target must have an explicit Git-disconnected workspace ID."
    }
}
if (-not $config.dev_workspace.workspace_id -or $config.dev_workspace.git_connected -ne $true) {
    throw 'Configured DEV workspace must have an explicit Git-connected workspace ID.'
}

$targets = [ordered]@{ DEV = $config.dev_workspace.workspace_id }
foreach ($property in $config.targets.PSObject.Properties) { $targets[$property.Name] = $property.Value.workspace_id }
$record = [ordered]@{
    captured_at = (Get-Date).ToUniversalTime().ToString('o')
    action = 'workspace-reconciliation-plan'
    workspaces = $targets
    proposed_actions = @('reconcile only explicitly mapped workspace roles through developer-authenticated fab')
    external_writes = $false
}
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $EvidencePath) | Out-Null
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $EvidencePath -Encoding utf8
