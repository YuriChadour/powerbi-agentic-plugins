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
if ($source -match 'Convert-AgentMarkdownToCodexToml') { throw 'Installer must not generate Codex agent adapters.' }
if ($source -notmatch 'Test-AgentAdapterParity') { throw 'Checked-in Codex adapter parity validation is missing.' }
& (Join-Path $repo 'scripts\validate-codex-catalog.ps1') -RepositoryPath $repo | Out-Null
foreach ($agent in Get-ChildItem $repo -Recurse -File | Where-Object { $_.Directory.Name -eq 'agents' -and $_.Directory.FullName -match '\\plugins\\[^\\]+\\agents$' -and $_.Extension -eq '.md' }) {
    $adapterName = "$( ([IO.Path]::GetFileNameWithoutExtension($agent.Name) -replace '\.agent$','') ).toml"
    $adapter = Join-Path $agent.DirectoryName $adapterName
    if (-not (Test-Path $adapter)) { throw "Checked-in Codex adapter is missing: $adapter" }
}
foreach ($adapter in Get-ChildItem $repo -Recurse -File | Where-Object { $_.Directory.Name -eq 'agents' -and $_.Directory.FullName -match '\\plugins\\[^\\]+\\agents$' -and $_.Extension -eq '.toml' }) {
    $candidateNames = @("$([IO.Path]::GetFileNameWithoutExtension($adapter.Name)).agent.md", "$([IO.Path]::GetFileNameWithoutExtension($adapter.Name)).md")
    if (-not (@(Get-ChildItem $adapter.DirectoryName -File | Where-Object { $candidateNames -contains $_.Name }).Count)) {
        throw "Orphaned Codex adapter: $($adapter.FullName)"
    }
}
Write-Output 'Static setup contract OK.'
if (-not $RunIntegration) { return }
function Invoke-IsolatedSetup {
    param(
        [string]$Profile,
        [hashtable]$Arguments
    )
    $oldProfile = $env:USERPROFILE
    try {
        $env:USERPROFILE = $Profile
        & $setup @Arguments
        return $LASTEXITCODE
    } catch {
        # Parameter-binding failures (for example ValidateSet rejection) are
        # terminating errors in an in-process invocation; normalize them to
        # the same nonzero result a child process would return.
        return 1
    } finally {
        $env:USERPROFILE = $oldProfile
    }
}

function New-TestProfile {
    $profile = Join-Path ([IO.Path]::GetTempPath()) ('pbi-setup-test-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $profile -Force | Out-Null
    return $profile
}

function New-DevopsFixture {
    param([string]$Profile)
    $fixture = Join-Path $Profile 'fixture'
    New-Item -ItemType Directory -Path (Join-Path $fixture '.git'),(Join-Path $fixture '.claude-plugin'),(Join-Path $fixture 'plugins') -Force | Out-Null
    Copy-Item (Join-Path $repo '.claude-plugin\marketplace.json') (Join-Path $fixture '.claude-plugin\marketplace.json')
    Copy-Item (Join-Path $repo 'plugins\devops') (Join-Path $fixture 'plugins') -Recurse
    return $fixture
}

$profiles = @()
try {
    # Codex-only and selected-plugin projection.
    $codexProfile = New-TestProfile; $profiles += $codexProfile
    $code = Invoke-IsolatedSetup -Profile $codexProfile -Arguments @{ RepositoryPath=$repo; Target='Codex'; PluginName='fabric' }
    if ($code -ne 0) { throw 'Codex isolated install failed.' }
    & (Join-Path $repo 'scripts\validate-codex-projection.ps1') -RepositoryPath $repo -ProjectionRoot (Join-Path $codexProfile '.codex')
    if (Test-Path (Join-Path $codexProfile '.copilot')) { throw 'Codex-only setup touched Copilot state.' }
    Write-Output 'Codex selected-plugin projection OK.'

    # Copilot-only projection remains independent of Codex.
    $copilotProfile = New-TestProfile; $profiles += $copilotProfile
    $code = Invoke-IsolatedSetup -Profile $copilotProfile -Arguments @{ RepositoryPath=$repo; Target='Copilot'; PluginName='fabric'; SkipCopilotCLI=$true; SkipVSCode=$true }
    if ($code -ne 0) { throw 'Copilot isolated install failed.' }
    if (-not (Test-Path (Join-Path $copilotProfile '.copilot\extensions\fabric\skills\fabric-cli\SKILL.md'))) { throw 'Copilot fabric projection is missing.' }
    if (Test-Path (Join-Path $copilotProfile '.codex')) { throw 'Copilot-only setup touched Codex state.' }
    Write-Output 'Copilot selected-plugin projection OK.'

    # Missing Node.js is optional for the fabric Copilot projection. Remove its
    # PATH segment for this disposable run and verify setup remains successful.
    $optionalProfile = New-TestProfile; $profiles += $optionalProfile
    $oldPath = $env:PATH
    try {
        $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
        if ($nodeCommand) {
            $nodeDirectory = Split-Path $nodeCommand.Source -Parent
            $env:PATH = (($env:PATH -split ';' | Where-Object { $_ -and $_ -ne $nodeDirectory }) -join ';')
        }
        $code = Invoke-IsolatedSetup -Profile $optionalProfile -Arguments @{ RepositoryPath=$repo; Target='Copilot'; PluginName='fabric'; SkipCopilotCLI=$true; SkipVSCode=$true }
    } finally {
        $env:PATH = $oldPath
    }
    if ($code -ne 0) { throw 'Copilot setup failed when optional Node.js was unavailable.' }
    Write-Output 'Missing optional dependency behavior OK.'

    # Omitted Target defaults to All; explicit All with -Force exercises the update path.
    $allProfile = New-TestProfile; $profiles += $allProfile
    $code = Invoke-IsolatedSetup -Profile $allProfile -Arguments @{ RepositoryPath=$repo; PluginName='fabric'; SkipCopilotCLI=$true; SkipVSCode=$true }
    if ($code -ne 0) { throw 'Default All install failed.' }
    & (Join-Path $repo 'scripts\validate-codex-projection.ps1') -RepositoryPath $repo -ProjectionRoot (Join-Path $allProfile '.codex')
    $code = Invoke-IsolatedSetup -Profile $allProfile -Arguments @{ RepositoryPath=$repo; Target='All'; PluginName='fabric'; Force=$true; SkipCopilotCLI=$true; SkipVSCode=$true }
    if ($code -ne 0) { throw 'Explicit All force update failed.' }
    if (-not (Get-ChildItem (Join-Path $allProfile '.codex\backups') -Directory -ErrorAction SilentlyContinue)) { throw 'Force update did not create a Codex backup.' }
    Write-Output 'Default and explicit All projections OK.'

    # Non-force rerun must fail without deleting the existing projection.
    $code = Invoke-IsolatedSetup -Profile $codexProfile -Arguments @{ RepositoryPath=$repo; Target='Codex'; PluginName='fabric' }
    if ($code -eq 0) { throw 'Non-force Codex rerun unexpectedly succeeded.' }
    if (-not (Test-Path (Join-Path $codexProfile '.codex\powerbi-agentic-plugins.manifest.json'))) { throw 'Non-force rerun removed the Codex manifest.' }
    Write-Output 'Non-force collision behavior OK.'

    # Invalid selectors and an explicit missing repository must fail before either target writes.
    $invalidProfile = New-TestProfile; $profiles += $invalidProfile
    $code = Invoke-IsolatedSetup -Profile $invalidProfile -Arguments @{ RepositoryPath=$repo; Target='InvalidTarget'; SkipCopilotCLI=$true; SkipVSCode=$true }
    if ($code -eq 0 -or (Test-Path (Join-Path $invalidProfile '.codex')) -or (Test-Path (Join-Path $invalidProfile '.copilot'))) { throw 'Invalid target was not rejected before writes.' }
    $code = Invoke-IsolatedSetup -Profile $invalidProfile -Arguments @{ RepositoryPath=$repo; PluginName='invalid-plugin'; SkipCopilotCLI=$true; SkipVSCode=$true }
    if ($code -eq 0 -or (Test-Path (Join-Path $invalidProfile '.codex')) -or (Test-Path (Join-Path $invalidProfile '.copilot'))) { throw 'Invalid plugin was not rejected before writes.' }
    $code = Invoke-IsolatedSetup -Profile $invalidProfile -Arguments @{ RepositoryPath=(Join-Path $invalidProfile 'missing-repository'); Target='Codex' }
    if ($code -eq 0 -or (Test-Path (Join-Path $invalidProfile '.codex'))) { throw 'Missing repository was not rejected before writes.' }
    Write-Output 'Invalid selector and missing repository behavior OK.'

    # A disposable source checkout with a missing or invalid adapter must fail
    # source validation before Codex projection begins.
    $missingAdapterProfile = New-TestProfile; $profiles += $missingAdapterProfile
    $missingAdapterRepo = New-DevopsFixture -Profile $missingAdapterProfile
    Remove-Item (Join-Path $missingAdapterRepo 'plugins\devops\agents\devops.toml') -Force
    $code = Invoke-IsolatedSetup -Profile $missingAdapterProfile -Arguments @{ RepositoryPath=$missingAdapterRepo; Target='Codex'; PluginName='devops' }
    if ($code -eq 0 -or (Test-Path (Join-Path $missingAdapterProfile '.codex'))) { throw 'Missing adapter was not rejected before projection.' }

    $staleAdapterProfile = New-TestProfile; $profiles += $staleAdapterProfile
    $staleAdapterRepo = New-DevopsFixture -Profile $staleAdapterProfile
    $staleAdapterPath = Join-Path $staleAdapterRepo 'plugins\devops\agents\devops.toml'
    Add-Content -LiteralPath $staleAdapterPath -Value "`n# stale adapter fixture"
    $code = Invoke-IsolatedSetup -Profile $staleAdapterProfile -Arguments @{ RepositoryPath=$staleAdapterRepo; Target='Codex'; PluginName='devops' }
    if ($code -eq 0 -or (Test-Path (Join-Path $staleAdapterProfile '.codex'))) { throw 'Stale adapter was not rejected before projection.' }
    Write-Output 'Missing and stale adapter behavior OK.'

    # Inject a user-owned Codex MCP conflict. All must leave Copilot usable while
    # reporting Codex failure and preserving the conflicting configuration.
    $failureProfile = New-TestProfile; $profiles += $failureProfile
    $codexRoot = Join-Path $failureProfile '.codex'
    New-Item -ItemType Directory -Path $codexRoot -Force | Out-Null
    $conflictConfig = "[mcp_servers.fabric-mcp-server]`ncommand = 'user-owned'`nargs = []`n"
    Set-Content -LiteralPath (Join-Path $codexRoot 'config.toml') -Value $conflictConfig -Encoding UTF8
    $code = Invoke-IsolatedSetup -Profile $failureProfile -Arguments @{ RepositoryPath=$repo; Target='All'; PluginName='fabric'; SkipCopilotCLI=$true; SkipVSCode=$true }
    if ($code -eq 0) { throw 'Injected Codex MCP conflict did not fail the All run.' }
    if (-not (Test-Path (Join-Path $failureProfile '.copilot\extensions\fabric\skills\fabric-cli\SKILL.md'))) { throw 'Copilot did not remain usable after Codex failure.' }
    if ((Get-Content (Join-Path $codexRoot 'config.toml') -Raw) -notmatch 'user-owned') { throw 'Codex conflict configuration was overwritten.' }
    Write-Output 'Injected one-target failure behavior OK.'
} finally {
    foreach ($profile in $profiles) {
        if (Test-Path $profile) { Remove-Item -LiteralPath $profile -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

# Make the successful integration result explicit for CI callers. Terminating
# assertion failures above still produce a nonzero process result.
exit 0
