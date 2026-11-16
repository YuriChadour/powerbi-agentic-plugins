[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('Render', 'Plan', 'Apply', 'Status', 'Resume', 'Deploy')]
    [string]$Mode,
    [Parameter(Mandatory)] [string]$ConfigPath,
    [Parameter(Mandatory)] [string]$ManifestPath,
    [string]$RepoRoot = (Get-Location).Path,
    [string]$OutputRoot,
    [string]$Target,
    [string]$ArtifactPath,
    [switch]$AllowOverwrite,
    [switch]$AllowTargetWrite
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-Python { foreach ($candidate in @('py', 'python')) { if (Get-Command $candidate -ErrorAction SilentlyContinue) { return $candidate } }; throw 'Python 3 is required.' }
function Get-HelperPath {
    $installed = Join-Path $PSScriptRoot 'scripts/powerbi_cicd.py'
    if (Test-Path -LiteralPath $installed) { return $installed }
    $source = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'scripts/powerbi_cicd.py'
    if (Test-Path -LiteralPath $source) { return $source }
    throw 'Cannot locate scripts/powerbi_cicd.py.'
}
function Invoke-Helper([string[]]$Arguments) {
    $python = Get-Python
    $prefix = if ($python -eq 'py') { @('-3') } else { @() }
    $result = & $python @prefix (Get-HelperPath) @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw ($result -join [Environment]::NewLine) }
    $result -join [Environment]::NewLine
}

$arguments = @('--config', $ConfigPath, '--manifest', $ManifestPath, '--repo', $RepoRoot)
switch ($Mode) {
    'Plan' { Invoke-Helper (@('plan') + $arguments); break }
    'Render' {
        $destination = if ($OutputRoot) { $OutputRoot } else { Join-Path $RepoRoot 'cicd' }
        Invoke-Helper (@('render', '--output', $destination) + $(if ($AllowOverwrite) { @('--allow-overwrite') } else { @() }) + $arguments); break
    }
    'Status' { Invoke-Helper (@('status') + $arguments); break }
    default {
        if ($Mode -eq 'Deploy' -and (-not $Target -or -not $ArtifactPath -or -not $AllowTargetWrite)) { throw 'Deploy requires -Target, -ArtifactPath, and -AllowTargetWrite.' }
        throw "$Mode is fail-closed until a tenant-approved supported-item matrix and protected deployment adapter are available."
    }
}
