#Requires -Version 5.1
<# Validates a materialized Codex projection against the repository catalog. #>
[CmdletBinding()]
param(
    [string]$RepositoryPath = (Split-Path $PSScriptRoot -Parent),
    [string]$ProjectionRoot = (Join-Path $env:USERPROFILE '.codex')
)
$ErrorActionPreference = 'Stop'
$marketplace = Get-Content (Join-Path $RepositoryPath '.claude-plugin\marketplace.json') -Raw | ConvertFrom-Json
$catalogPlugins = @($marketplace.plugins | ForEach-Object name)
$manifestPath = Join-Path $ProjectionRoot 'powerbi-agentic-plugins.manifest.json'
if (-not (Test-Path $manifestPath)) { throw "Codex manifest not found: $manifestPath" }
$manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
if ($manifest.owner -ne 'powerbi-agentic-plugins') { throw 'Projection manifest has an unexpected owner.' }
$plugins = @($manifest.plugins)
if ($plugins.Count -eq 0) { throw 'Projection manifest contains no plugins.' }
if (@(Compare-Object $plugins ($plugins | Where-Object { $catalogPlugins -contains $_ })).Count) { throw 'Projection contains an undeclared plugin.' }
foreach ($plugin in $plugins) {
    $source = Join-Path $RepositoryPath "plugins\$plugin"
    if (-not (Test-Path $source -PathType Container)) { throw "Missing source plugin: $plugin" }
    foreach ($skill in Get-ChildItem (Join-Path $source 'skills') -Directory) {
        $projected = Join-Path $ProjectionRoot "skills\$($skill.Name)"
        if (-not (Test-Path (Join-Path $projected 'SKILL.md'))) { throw "Missing projected skill: $plugin/$($skill.Name)" }
        if ((Get-FileHash (Join-Path $skill.FullName 'SKILL.md')).Hash -ne (Get-FileHash (Join-Path $projected 'SKILL.md')).Hash) { throw "Skill content drift: $plugin/$($skill.Name)" }
    }
    foreach ($agent in Get-ChildItem (Join-Path $source 'agents') -Filter '*.agent.md' -File -ErrorAction SilentlyContinue) {
        $name = $agent.Name -replace '\.agent\.md$','.md'
        $projected = Join-Path $ProjectionRoot "agents\$name"
        $adapter = [IO.Path]::ChangeExtension($projected, '.toml')
        if (-not (Test-Path $projected) -or -not (Test-Path $adapter)) { throw "Missing projected agent or adapter: $plugin/$($agent.Name)" }
        if ((Get-FileHash $agent.FullName).Hash -ne (Get-FileHash $projected).Hash) { throw "Agent instruction drift: $plugin/$($agent.Name)" }
        if ((Get-Content $adapter -Raw) -notmatch [regex]::Escape($name)) { throw "Agent adapter does not reference source instruction: $adapter" }
    }
}
Write-Output "Projection OK: plugins=$($plugins.Count), skills=$(@($manifest.skills).Count), agents=$(@($manifest.agents).Count)"
