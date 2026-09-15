# Lightweight integration checks for the target dispatcher. Run with PowerShell 5.1+.
[CmdletBinding()]
param([switch]$RunIntegration)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$setup = Join-Path $repo 'setup-team-plugins.ps1'
if (-not (Test-Path $setup)) { throw 'setup-team-plugins.ps1 is missing.' }
$source = Get-Content $setup -Raw
foreach ($required in @('-Target', 'Codex', 'Copilot', 'All', '-Force', 'powerbi-agentic-plugins.manifest.json', 'config.toml')) {
    if ($source -notmatch [regex]::Escape($required)) { throw "Installer contract is missing: $required" }
}
if ($source -notmatch '\$Target\s*=\s*"All"') { throw 'Target default is not All.' }
if ($source -notmatch 'Test-CopilotDestinations') { throw 'Copilot collision preflight is missing.' }
if ($source -notmatch 'Test-CodexCapabilities') { throw 'Codex capability checks are missing.' }
Write-Output 'Static setup contract OK.'
if (-not $RunIntegration) { return }
$profile = Join-Path ([IO.Path]::GetTempPath()) ('pbi-setup-test-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $profile -Force | Out-Null
$oldProfile = $env:USERPROFILE
try {
    $env:USERPROFILE = $profile
    & $setup -RepositoryPath $repo -Target Codex -PluginName fabric
    if ($LASTEXITCODE -ne 0) { throw 'Codex isolated install failed.' }
    & (Join-Path $repo 'scripts\validate-codex-projection.ps1') -RepositoryPath $repo -ProjectionRoot (Join-Path $profile '.codex')
    Write-Output 'Codex isolated projection OK.'
} finally { $env:USERPROFILE = $oldProfile }
