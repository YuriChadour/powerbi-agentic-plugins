param(
    [ValidateSet('unknown', 'fabric-data-engineering-only', 'power-bi', 'other', 'mixed')]
    [string]$Scope = 'unknown',
    [string]$DevBranch,
    [ValidateSet('bug', 'feature', 'story')]
    [string]$WorkType,
    [ValidatePattern('^[A-Z][A-Z0-9]*-[0-9]+$')]
    [string]$Ticket
)

$ErrorActionPreference = 'Continue'
if ([string]::IsNullOrWhiteSpace($WorkType) -xor [string]::IsNullOrWhiteSpace($Ticket)) {
    Write-Host 'Supply both the selected work type and user-provided Jira ticket when passing intake context.' -ForegroundColor Red
    exit 1
}
$protectedBranches = @('main', 'master', 'prod', 'production', 'dev', 'develop', 'test')
$neverDevBranches = @('main', 'master', 'prod', 'production', 'test')
$allowedPrefixes = @('bugfix/', 'feature/')

$currentBranch = git branch --show-current
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($currentBranch)) {
    Write-Host 'Could not determine the current Git branch. Check the repository and leave detached HEAD before continuing.' -ForegroundColor Red
    exit 1
}
$currentBranch = $currentBranch.Trim()

if ($Scope -eq 'fabric-data-engineering-only') {
    if ([string]::IsNullOrWhiteSpace($DevBranch) -or $DevBranch -cne $DevBranch.Trim()) {
        Write-Host 'Configure the exact DEV working branch before requesting the Fabric data-engineering exception.' -ForegroundColor Red
        exit 1
    }
    $validatedBranch = git check-ref-format --branch $DevBranch 2>$null
    if ($LASTEXITCODE -ne 0 -or $validatedBranch -cne $DevBranch -or $neverDevBranches -contains $DevBranch) {
        Write-Host "Configured DEV branch '$DevBranch' is invalid or protected. Choose a valid permitted DEV branch." -ForegroundColor Red
        exit 1
    }
    $repoRoot = git rev-parse --show-toplevel
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($repoRoot)) {
        Write-Host 'Could not determine the Git repository root.' -ForegroundColor Red
        exit 1
    }
    $pluginRepo = (Test-Path (Join-Path $repoRoot '.claude-plugin/marketplace.json')) -and
        (Test-Path (Join-Path $repoRoot 'plugins/devops/skills/git-branch-guard/check_git_branch_guard.ps1'))
    if (-not $pluginRepo -and $currentBranch -ceq $DevBranch) {
        Write-Host "Configured DEV branch '$currentBranch' is valid for exclusive Fabric data engineering." -ForegroundColor Green
        exit 0
    }
}

if ($protectedBranches -contains $currentBranch) {
    Write-Host "Current branch '$currentBranch' is protected. Create a bugfix/ or feature/ branch with a Jira key before continuing." -ForegroundColor Red
    exit 1
}
if (-not ($allowedPrefixes | Where-Object { $currentBranch.StartsWith($_, [System.StringComparison]::Ordinal) })) {
    Write-Host "Branch '$currentBranch' must start with 'bugfix/' or 'feature/'." -ForegroundColor Red
    exit 1
}
if ($currentBranch -cnotmatch '[A-Z]+-\d+') {
    Write-Host "Branch '$currentBranch' must include an uppercase Jira key like ABC-123." -ForegroundColor Red
    exit 1
}
Write-Host "Branch '$currentBranch' is valid." -ForegroundColor Green
