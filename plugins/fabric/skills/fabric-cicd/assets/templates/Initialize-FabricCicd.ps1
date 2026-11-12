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

function Invoke-External {
    param([Parameter(Mandatory)] [string]$File, [Parameter(ValueFromRemainingArguments)] [string[]]$Arguments)
    $result = & $File @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "$File failed: $($result -join [Environment]::NewLine)" }
    return ($result -join [Environment]::NewLine)
}

function Get-Python {
    foreach ($candidate in @('py', 'python')) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) { return $candidate }
    }
    throw 'Python 3 is required for the offline bootstrap helper.'
}

function Get-HelperPath {
    $installed = Join-Path $PSScriptRoot 'scripts/bootstrap.py'
    if (Test-Path -LiteralPath $installed) { return $installed }
    $source = Join-Path (Split-Path -Parent (Split-Path -Parent $PSScriptRoot)) 'scripts/bootstrap.py'
    if (Test-Path -LiteralPath $source) { return $source }
    throw 'Cannot locate scripts/bootstrap.py. Use the rendered CI copy or the installed skill template.'
}

function Invoke-HelperJson {
    param([string[]]$Arguments)
    $python = Get-Python
    $raw = Invoke-External $python (,@(if ($python -eq 'py') { '-3' }) + @((Get-HelperPath)) + $Arguments)
    return $raw | ConvertFrom-Json
}

function Get-Config {
    $config = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    $validation = Invoke-HelperJson @('validate', '--config', $ConfigPath, '--manifest', $ManifestPath)
    if ($validation.status -ne 'valid') { throw "Bootstrap input is invalid: $($validation | ConvertTo-Json -Compress)" }
    return $config
}

function Assert-DeveloperSetupSessions {
    # Setup always uses the developer's current, interactive fab and az sessions.
    # There are intentionally no token, client-secret, or service-principal parameters here.
    Invoke-External 'fab' @('auth', 'status') | Out-Null
    Invoke-External 'az' @('account', 'show', '--output', 'none') | Out-Null
    Invoke-External 'az' @('extension', 'show', '--name', 'azure-devops', '--output', 'none') | Out-Null
}

function Get-Workspace {
    param($TargetConfig)
    $path = "$($TargetConfig.workspace_name).Workspace"
    $existsOutput = & fab exists $path 2>&1
    if ($LASTEXITCODE -ne 0) { throw "fab exists failed: $($existsOutput -join [Environment]::NewLine)" }
    $exists = ($existsOutput -join [Environment]::NewLine).Trim().ToLowerInvariant() -eq 'true'
    if (-not $exists) {
        if (-not $TargetConfig.capacity_name) { throw "Workspace '$($TargetConfig.workspace_name)' was not found and no capacity_name is configured." }
        Invoke-External 'fab' @('mkdir', $path, '-P', "capacityname=$($TargetConfig.capacity_name)", '-f') | Out-Null
    }
    $id = (Invoke-External 'fab' @('get', $path, '-q', 'id')).Trim('"', "'", ' ')
    if ($TargetConfig.workspace_id -and $TargetConfig.workspace_id.ToString().ToLowerInvariant() -ne $id.ToLowerInvariant()) {
        throw "Workspace '$($TargetConfig.workspace_name)' resolved to an ID different from the configured workspace_id."
    }
    return [pscustomobject]@{ Id = $id; Path = $path; Name = $TargetConfig.workspace_name }
}

function Ensure-WorkspaceRoles {
    param($Workspace, [object[]]$Mappings)
    $response = Invoke-External 'fab' @('api', "workspaces/$($Workspace.Id)/roleAssignments") | ConvertFrom-Json
    $assignments = @($response.value)
    foreach ($mapping in $Mappings) {
        $matching = @($assignments | Where-Object { $_.principal.id -eq $mapping.object_id })
        if ($matching.Count -gt 0) {
            if ($matching[0].principal.type -ne $mapping.principal_type -or $matching[0].role -ne $mapping.role) {
                throw "Existing direct role for '$($mapping.object_id)' in '$($Workspace.Name)' differs from the approved mapping; it was not changed."
            }
            continue
        }
        $payload = @{ principal = @{ id = $mapping.object_id; type = $mapping.principal_type }; role = $mapping.role } | ConvertTo-Json -Compress
        Invoke-External 'fab' @('api', '-X', 'post', "workspaces/$($Workspace.Id)/roleAssignments", '-i', $payload) | Out-Null
    }
    # Read-after-write confirms only the mappings this bootstrap owns.
    $confirmed = Invoke-External 'fab' @('api', "workspaces/$($Workspace.Id)/roleAssignments") | ConvertFrom-Json
    foreach ($mapping in $Mappings) {
        if (-not @($confirmed.value | Where-Object { $_.principal.id -eq $mapping.object_id -and $_.principal.type -eq $mapping.principal_type -and $_.role -eq $mapping.role })) {
            throw "Fabric did not confirm the configured direct role for '$($mapping.object_id)' in '$($Workspace.Name)'."
        }
    }
}

function Assert-DevConnectionAndBaseline {
    param($Config, [string]$RepositoryRoot)
    $path = "$($Config.dev_workspace.workspace_name).Workspace"
    $existsOutput = & fab exists $path 2>&1
    if ($LASTEXITCODE -ne 0) { throw "fab exists failed while checking DEV: $($existsOutput -join [Environment]::NewLine)" }
    if (($existsOutput -join [Environment]::NewLine).Trim().ToLowerInvariant() -ne 'true') { throw "Configured DEV workspace '$($Config.dev_workspace.workspace_name)' does not exist." }
    $id = (Invoke-External 'fab' @('get', $path, '-q', 'id')).Trim('"', "'", ' ')
    if ($id.ToLowerInvariant() -ne $Config.dev_workspace.workspace_id.ToString().ToLowerInvariant()) { throw 'Configured DEV workspace ID does not match its name.' }
    $connection = Invoke-External 'fab' @('api', "workspaces/$id/git/connection") | ConvertFrom-Json
    if (-not $connection) { throw 'Configured DEV workspace has no verified Fabric Git connection.' }
    & git -C $RepositoryRoot cat-file -e "$($Config.repository.dev_branch):$($Config.repository.fabric_source_folder)" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Configured DEV branch lacks the required Fabric source baseline '$($Config.repository.fabric_source_folder)'." }
}

function Assert-YamlOnBranch {
    param($Pipeline, [string]$RepositoryRoot)
    & git -C $RepositoryRoot cat-file -e "$($Pipeline.source_branch):$($Pipeline.yaml_path)" 2>$null
    if ($LASTEXITCODE -ne 0) { throw "Pipeline YAML '$($Pipeline.yaml_path)' is not committed on '$($Pipeline.source_branch)'. Render, review and commit it first." }
}

function Ensure-AzurePipeline {
    param($Config, $Pipeline, [string]$RepositoryRoot)
    Assert-YamlOnBranch $Pipeline $RepositoryRoot
    $org = "https://dev.azure.com/$($Config.azure_devops.organization)"
    $arguments = @('pipelines', 'list', '--name', $Pipeline.name, '--repository', $Config.azure_devops.repository, '--repository-type', 'tfsgit', '--org', $org, '--project', $Config.azure_devops.project, '--output', 'json')
    $matches = @(Invoke-External 'az' $arguments | ConvertFrom-Json)
    if ($matches.Count -eq 0) {
        $created = Invoke-External 'az' @('pipelines', 'create', '--name', $Pipeline.name, '--repository', $Config.azure_devops.repository, '--repository-type', 'tfsgit', '--branch', $Pipeline.source_branch, '--yml-path', $Pipeline.yaml_path, '--skip-first-run', 'true', '--org', $org, '--project', $Config.azure_devops.project, '--output', 'json') | ConvertFrom-Json
        return $created.id
    }
    if ($matches.Count -ne 1) { throw "Azure DevOps returned multiple pipelines named '$($Pipeline.name)'." }
    $existing = Invoke-External 'az' @('pipelines', 'show', '--id', $matches[0].id, '--org', $org, '--project', $Config.azure_devops.project, '--output', 'json') | ConvertFrom-Json
    if ($existing.configuration.path -ne $Pipeline.yaml_path -or $existing.repository.name -ne $Config.azure_devops.repository -or $existing.repository.defaultBranch -notmatch [regex]::Escape($Pipeline.source_branch)) {
        throw "Azure Pipeline '$($Pipeline.name)' has a different repository, branch, or YAML path; it was not changed."
    }
    return $existing.id
}

function Render-File {
    param([string]$Source, [string]$Destination, [hashtable]$Tokens)
    if ((Test-Path -LiteralPath $Destination) -and -not $AllowOverwrite) { throw "Refusing to overwrite '$Destination'. Use -AllowOverwrite after reviewing the diff." }
    $content = Get-Content -LiteralPath $Source -Raw
    foreach ($key in $Tokens.Keys) { $content = $content.Replace("{{$key}}", [string]$Tokens[$key]) }
    if ($content -match '{{[a-z_]+}}') { throw "Unresolved template token in '$Source'." }
    New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
    Set-Content -LiteralPath $Destination -Value $content -NoNewline
}

function Render-Bootstrap {
    param($Config)
    $root = (Resolve-Path -LiteralPath $RepoRoot).Path
    $destination = if ($OutputRoot) { $OutputRoot } else { Join-Path $root $Config.repository.ci_folder }
    $templateRoot = $PSScriptRoot
    $tokens = @{
        fabric_source_folder = $Config.repository.fabric_source_folder; ci_folder = $Config.repository.ci_folder
        dev_branch = $Config.repository.dev_branch; prod_branch = $Config.repository.prod_branch
        test_environment = $Config.targets.TEST.environment; prod_environment = $Config.targets.PROD.environment
        test_variable_group = $Config.targets.TEST.variable_group; prod_variable_group = $Config.targets.PROD.variable_group
        test_write_guard = $Config.protected_resources.TEST.write_guard; prod_write_guard = $Config.protected_resources.PROD.write_guard
        test_service_connection = $Config.protected_resources.TEST.service_connection; prod_service_connection = $Config.protected_resources.PROD.service_connection
        test_pipeline_name = $Config.pipelines.TEST.name
    }
    foreach ($name in @('fabric-test.yml', 'fabric-prod.yml', 'validation-steps.yml', 'SETUP.md', 'verification-checklist.md')) {
        Render-File (Join-Path $templateRoot $name) (Join-Path $destination $name) $tokens
    }
    if ($Config.targets.PSObject.Properties.Name -contains 'UAT') {
        Render-File (Join-Path $templateRoot 'fabric-uat.yml') (Join-Path $destination 'fabric-uat.yml') $tokens
    }
    foreach ($copy in @(@{ From = (Get-HelperPath); To = (Join-Path $destination 'scripts/bootstrap.py') }, @{ From = $PSCommandPath; To = (Join-Path $destination 'Initialize-FabricCicd.ps1') })) {
        if ((Test-Path -LiteralPath $copy.To) -and -not $AllowOverwrite) { throw "Refusing to overwrite '$($copy.To)'. Use -AllowOverwrite after reviewing the diff." }
        New-Item -ItemType Directory -Path (Split-Path -Parent $copy.To) -Force | Out-Null
        Copy-Item -LiteralPath $copy.From -Destination $copy.To -Force
    }
    return $destination
}

function Deploy-Artifact {
    param($Config)
    if (-not $Target -or -not $ArtifactPath) { throw 'Deploy requires -Target and -ArtifactPath.' }
    if (-not $AllowTargetWrite) { throw 'Deploy requires -AllowTargetWrite.' }
    if (-not $Config.targets.PSObject.Properties.Name.Contains($Target)) { throw "Target '$Target' is not configured." }
    $guardName = "ALLOW_FABRIC_$Target`_WRITE"
    if ([Environment]::GetEnvironmentVariable($guardName) -ne 'true') { throw "Protected deployment guard '$guardName' must be exactly 'true'." }
    if (-not (Test-Path -LiteralPath $ArtifactPath)) { throw "Artifact '$ArtifactPath' was not found." }
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ("fabric-release-" + [guid]::NewGuid())
    try {
        Expand-Archive -LiteralPath $ArtifactPath -DestinationPath $temporary
        $release = Get-Content -LiteralPath (Join-Path $temporary 'release.json') -Raw | ConvertFrom-Json
        $expectedArtifactTarget = if ($Target -eq 'PROD') { 'TEST' } else { $Target }
        if ($release.target -ne $expectedArtifactTarget) { throw "Artifact target '$($release.target)' is not approved for '$Target'." }
        $items = Invoke-HelperJson @('managed-items', '--config', $ConfigPath, '--manifest', $ManifestPath)
        if ($items.status -ne 'valid') { throw 'Cannot read the managed items from the validated manifest.' }
        $workspacePath = "$($Config.targets.$Target.workspace_name).Workspace"
        $deployed = @()
        foreach ($item in $items.managed_items) {
            $source = Join-Path $temporary (Join-Path 'payload' (Join-Path $items.source_root $item.folder))
            $name = [IO.Path]::GetFileName($item.folder)
            Invoke-External 'fab' @('import', "$workspacePath/$name.$($item.type)", '-i', $source, '-f') | Out-Null
            $deployed += $item.folder
        }
        [pscustomobject]@{ deployment = 'succeeded'; target = $Target; managed_items = $deployed; verification = 'pending' } | ConvertTo-Json -Compress
    } finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force } }
}

$config = Get-Config
if ($Mode -eq 'Plan') { Invoke-HelperJson @('plan', '--config', $ConfigPath, '--manifest', $ManifestPath) | ConvertTo-Json -Depth 8; exit 0 }
if ($Mode -eq 'Render') { [pscustomobject]@{ status = 'rendered'; output = (Render-Bootstrap $config) } | ConvertTo-Json; exit 0 }
if ($Mode -eq 'Status') {
    $statePath = Join-Path (Join-Path (Resolve-Path -LiteralPath $RepoRoot) $config.repository.ci_folder) 'bootstrap-state.json'
    if (Test-Path -LiteralPath $statePath) { Get-Content -LiteralPath $statePath -Raw } else { '{"status":"not-applied"}' }
    exit 0
}
if ($Mode -eq 'Deploy') { Deploy-Artifact $config; exit 0 }
if ($Mode -eq 'Resume' -and -not (Test-Path -LiteralPath (Join-Path (Join-Path (Resolve-Path -LiteralPath $RepoRoot) $config.repository.ci_folder) 'bootstrap-state.json'))) { throw 'Nothing to resume: no redacted bootstrap state exists.' }

Assert-DeveloperSetupSessions
$resolvedRepositoryRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
Assert-DevConnectionAndBaseline $config $resolvedRepositoryRoot
$state = [ordered]@{ version = 1; applied_at_utc = [DateTime]::UtcNow.ToString('o'); targets = @{}; pipelines = @{} }
foreach ($targetName in $config.targets.PSObject.Properties.Name) {
    $workspace = Get-Workspace $config.targets.$targetName
    $mappings = @($config.roles | Where-Object { $_.target -eq $targetName })
    Ensure-WorkspaceRoles $workspace $mappings
    $state.targets[$targetName] = @{ workspace_name = $workspace.Name; workspace_id = $workspace.Id; direct_role_mappings = $mappings.Count }
}
foreach ($targetName in @('TEST', 'PROD')) { $state.pipelines[$targetName] = @{ id = (Ensure-AzurePipeline $config $config.pipelines.$targetName $resolvedRepositoryRoot); name = $config.pipelines.$targetName.name } }
$statePath = Join-Path (Join-Path (Resolve-Path -LiteralPath $RepoRoot) $config.repository.ci_folder) 'bootstrap-state.json'
New-Item -ItemType Directory -Path (Split-Path -Parent $statePath) -Force | Out-Null
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath
$state | ConvertTo-Json -Depth 8
