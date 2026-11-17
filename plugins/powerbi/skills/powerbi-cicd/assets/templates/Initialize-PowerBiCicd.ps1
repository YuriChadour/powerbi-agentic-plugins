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

function Get-ReviewPath {
    $root = (Resolve-Path -LiteralPath $RepoRoot).Path
    $destination = if ($OutputRoot) { $OutputRoot } else { Join-Path $root 'cicd' }
    return (Join-Path $destination 'CICD-SETUP.json')
}

function Assert-ApprovedReviewContract {
    $path = Get-ReviewPath
    if (-not (Test-Path -LiteralPath $path)) { throw "No rendered review contract exists at '$path'. Run Render, review it, and explicitly set approval to approved." }
    $approved = Get-Content -Raw -LiteralPath $path | ConvertFrom-Json
    if ($approved.approval -ne 'approved') { throw 'External setup is blocked until the developer explicitly approves the rendered non-secret contract.' }
    $temporary = Join-Path ([IO.Path]::GetTempPath()) ('powerbi-cicd-review-' + [guid]::NewGuid())
    try {
        Invoke-Helper (@('render', '--output', $temporary) + $arguments) | Out-Null
        $current = Get-Content -Raw -LiteralPath (Join-Path $temporary 'CICD-SETUP.json') | ConvertFrom-Json
        if ($approved.contract_revision -ne $current.contract_revision) { throw 'The approved review contract does not match the current configuration and manifest.' }
    } finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Recurse -Force } }
}

function Invoke-External {
    param([string]$File, [string[]]$Arguments)
    $result = & $File @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "$File failed: $($result -join [Environment]::NewLine)" }
    return ($result -join [Environment]::NewLine)
}

function Assert-DeveloperSessions {
    Invoke-External 'fab' @('auth', 'status') | Out-Null
    Invoke-External 'az' @('account', 'show', '--output', 'none') | Out-Null
    Invoke-External 'az' @('extension', 'show', '--name', 'azure-devops', '--output', 'none') | Out-Null
}

function Invoke-SetupGates {
    $config = Get-Content -Raw -LiteralPath $ConfigPath | ConvertFrom-Json
    $root = (Resolve-Path -LiteralPath $RepoRoot).Path
    $result = [ordered]@{ version = 1; completed_at_utc = [DateTime]::UtcNow.ToString('o'); gates = [ordered]@{}; targets = [ordered]@{}; external_writes = $true }

    # Repository gate: source root and generated YAML must be committed before registration.
    & git -C $root cat-file -e "$($config.repository.dev_branch):$($config.repository.powerbi_source_folder)" 2>$null
    if ($LASTEXITCODE -ne 0) { throw 'Repository gate failed: the configured DEV branch lacks the approved Power BI source boundary.' }
    $result.gates.repository = 'passed'

    # Workspace gate deliberately operates only on explicit workspace IDs and
    # direct mapped roles. Targets must stay Git-disconnected.
    foreach ($targetName in $config.targets.PSObject.Properties.Name) {
        $target = $config.targets.$targetName
        $workspace = Invoke-External 'fab' @('api', "workspaces/$($target.workspace_id)") | ConvertFrom-Json
        if ($workspace.id -ne $target.workspace_id -or $workspace.displayName -ne $target.workspace_name) { throw "Workspace gate failed for ${targetName}: configured ID/name mismatch." }
        $connection = Invoke-External 'fab' @('api', "workspaces/$($target.workspace_id)/git/connection")
        if (-not [string]::IsNullOrWhiteSpace($connection) -and $connection -ne 'null') { throw "Workspace gate failed for ${targetName}: deployment targets must be Git-disconnected." }
        $roles = @($config.roles | Where-Object { $_.target -eq $targetName })
        foreach ($role in $roles) {
            $assignments = (Invoke-External 'fab' @('api', "workspaces/$($target.workspace_id)/roleAssignments") | ConvertFrom-Json).value
            $matching = @($assignments | Where-Object { $_.principal.id -eq $role.object_id })
            if ($matching.Count -eq 0) {
                $payload = @{ principal = @{ id = $role.object_id; type = $role.principal_type }; role = $role.role } | ConvertTo-Json -Compress
                Invoke-External 'fab' @('api', '-X', 'post', "workspaces/$($target.workspace_id)/roleAssignments", '-i', $payload) | Out-Null
            } elseif ($matching.Count -ne 1 -or $matching[0].role -ne $role.role -or $matching[0].principal.type -ne $role.principal_type) {
                throw "Workspace gate failed for ${targetName}: direct role mapping conflicts with the approved contract."
            }
        }
        $result.targets[$targetName] = @{ workspace_id = $target.workspace_id; git_connected = $false; direct_roles = $roles.Count }
    }
    $result.gates.workspace = 'passed'

    # Identity gate records references only.  Setup never resolves or uses a
    # protected runtime identity, service-principal secret, or variable group.
    foreach ($targetName in $config.targets.PSObject.Properties.Name) {
        if ([string]::IsNullOrWhiteSpace($config.protected_resources.$targetName.identity_reference)) { throw "Identity gate failed for $targetName." }
    }
    $result.gates.identity_and_secret = 'passed'

    # Governance gate keeps dev unprotected and makes test/main PR-only.
    $organization = "https://dev.azure.com/$($config.azure_devops.organization)"
    $repo = $config.azure_devops.repository
    foreach ($branch in @('test', 'main')) {
        $policies = Invoke-External 'az' @('repos', 'policy', 'list', '--organization', $organization, '--project', $config.azure_devops.project, '--repository', $repo, '--output', 'json') | ConvertFrom-Json
        $matching = @($policies | Where-Object { $_.isEnabled -eq $true -and $_.isBlocking -eq $true -and $_.settings.scope.refName -eq "refs/heads/$branch" })
        if ($matching.Count -eq 0) { throw "Governance gate failed: $branch requires a blocking PR policy." }
    }
    $result.gates.governance = 'passed'

    # Each configured profile has a named pipeline. HOTFIX uses its isolated
    # profile; optional UAT/REHEARSAL profiles are included only when mapped.
    foreach ($profileName in $config.pipelines.PSObject.Properties.Name) {
        $pipelineConfig = $config.pipelines.$profileName
        $pipeline = @(Invoke-External 'az' @('pipelines', 'list', '--name', $pipelineConfig.name, '--repository', $repo, '--repository-type', 'tfsgit', '--organization', $organization, '--project', $config.azure_devops.project, '--output', 'json') | ConvertFrom-Json)
        if ($pipeline.Count -eq 0) {
            & git -C $root cat-file -e "$($pipelineConfig.source_branch):$($pipelineConfig.yaml_path)" 2>$null
            if ($LASTEXITCODE -ne 0) { throw "Pilot gate failed: $profileName YAML is not committed on '$($pipelineConfig.source_branch)'." }
            $created = Invoke-External 'az' @('pipelines', 'create', '--name', $pipelineConfig.name, '--repository', $repo, '--repository-type', 'tfsgit', '--branch', $pipelineConfig.source_branch, '--yml-path', $pipelineConfig.yaml_path, '--skip-first-run', 'true', '--organization', $organization, '--project', $config.azure_devops.project, '--output', 'json') | ConvertFrom-Json
            $pipeline = @($created)
        }
        if ($pipeline.Count -ne 1) { throw "Pilot gate failed: named $profileName pipeline '$($pipelineConfig.name)' must exist exactly once." }
    }
    $result.gates.pilot = 'passed'
    return $result
}

$arguments = @('--config', $ConfigPath, '--manifest', $ManifestPath, '--repo', $RepoRoot)
switch ($Mode) {
    'Plan' { Invoke-Helper (@('plan') + $arguments); break }
    'Render' {
        $destination = if ($OutputRoot) { $OutputRoot } else { Join-Path $RepoRoot 'cicd' }
        Invoke-Helper (@('render', '--output', $destination) + $(if ($AllowOverwrite) { @('--allow-overwrite') } else { @() }) + $arguments); break
    }
    'Status' {
        $path = Get-ReviewPath
        if (-not (Test-Path -LiteralPath $path)) { '{"status":"not-rendered","external_writes":false}'; break }
        $review = Get-Content -Raw -LiteralPath $path | ConvertFrom-Json
        [pscustomobject]@{
            status = if ($review.approval -eq 'approved') { 'approved-awaiting-apply' } else { 'awaiting-developer-approval' }
            contract_revision = $review.contract_revision
            approval = $review.approval
            targets = @($review.targets.PSObject.Properties.Name)
            external_writes = $false
        } | ConvertTo-Json -Depth 5
        break
    }
    'Apply' {
        Assert-ApprovedReviewContract
        Assert-DeveloperSessions
        $state = Invoke-SetupGates
        $statePath = Join-Path (Split-Path -Parent (Get-ReviewPath)) 'bootstrap-state.json'
        $state | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $statePath -Encoding utf8
        $state | ConvertTo-Json -Depth 10
    }
    'Resume' {
        Assert-ApprovedReviewContract
        Assert-DeveloperSessions
        Invoke-SetupGates | ConvertTo-Json -Depth 10
    }
    default {
        if ($Mode -eq 'Deploy' -and (-not $Target -or -not $ArtifactPath -or -not $AllowTargetWrite)) { throw 'Deploy requires -Target, -ArtifactPath, and -AllowTargetWrite.' }
        throw "$Mode is fail-closed until a tenant-approved supported-item matrix and protected deployment adapter are available."
    }
}
