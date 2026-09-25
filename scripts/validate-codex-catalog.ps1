#Requires -Version 5.1
<#
.SYNOPSIS
    Static source-catalog parity check for the Codex projection.
#>
[CmdletBinding()]
param([string]$RepositoryPath = (Split-Path $PSScriptRoot -Parent))

$ErrorActionPreference = 'Stop'
$expected = @('powerbi', 'fabric', 'devops', 'skill-creator', 'spec-lifecycle')
$marketplace = Get-Content (Join-Path $RepositoryPath '.claude-plugin\marketplace.json') -Raw | ConvertFrom-Json
$declared = @($marketplace.plugins | ForEach-Object { $_.name })
if (@(Compare-Object $expected $declared).Count) { throw 'Marketplace and supported plugin catalog differ.' }

$skillCount = 0; $agentCount = 0; $mcpCount = 0
$excludedSkillDirectories = @('paginated-report-authoring')
foreach ($plugin in $expected) {
    $root = Join-Path $RepositoryPath "plugins\$plugin"
    if (-not (Test-Path $root -PathType Container)) { throw "Missing plugin root: $plugin" }
    foreach ($skill in Get-ChildItem (Join-Path $root 'skills') -Directory) {
        if ($excludedSkillDirectories -contains $skill.Name) { continue }
        if (-not (Test-Path (Join-Path $skill.FullName 'SKILL.md'))) { throw "Missing SKILL.md: $($skill.FullName)" }
        $skillCount++
    }
    $agentCount += @(Get-ChildItem (Join-Path $root 'agents') -Filter '*.agent.md' -File -ErrorAction SilentlyContinue).Count
    foreach ($mcp in Get-ChildItem $root -Filter '.mcp.json' -File -ErrorAction SilentlyContinue) {
        Get-Content $mcp.FullName -Raw | ConvertFrom-Json | Out-Null
        $mcpCount++
    }
}
Write-Output "Catalog OK: plugins=$($expected.Count), skills=$skillCount, agents=$agentCount, mcp=$mcpCount"
