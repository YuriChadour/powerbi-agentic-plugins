$ErrorActionPreference = 'Stop'
$guard = (Resolve-Path (Join-Path $PSScriptRoot '../check_git_branch_guard.ps1')).Path
$base = [System.IO.Path]::GetTempPath().TrimEnd([System.IO.Path]::DirectorySeparatorChar)
$root = Join-Path $base ('branch-guard-test-' + [guid]::NewGuid())
New-Item -ItemType Directory $root | Out-Null
try {
    Push-Location $root
    git init -q
    git config user.email test@example.invalid
    git config user.name Test
    git commit --allow-empty -qm initial
    function Check([string]$branch, [string[]]$guardArgs, [int]$expected) {
        git checkout -q -B $branch
        $previousPreference = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'Continue'
            & powershell -NoProfile -File $guard @guardArgs *> $null
            $guardExit = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $previousPreference
        }
        if ($guardExit -ne $expected) { throw "Unexpected exit for $branch args [$guardArgs]: $guardExit (expected $expected)" }
    }
    Check dev @('-Scope','fabric-data-engineering-only','-DevBranch','dev') 0
    Check dev @('-Scope','fabric-data-engineering-only','-DevBranch','dev','-WorkType','feature','-Ticket','FIN-2060') 0
    Check dev @('-Scope','fabric-data-engineering-only','-DevBranch','dev','-WorkType','unknown','-Ticket','FIN-2060') 1
    Check dev @('-Scope','fabric-data-engineering-only','-DevBranch','dev','-WorkType','feature','-Ticket','invalid') 1
    Check dev @('-Scope','fabric-data-engineering-only','-DevBranch','dev','-WorkType','feature') 1
    Check integration @('-Scope','fabric-data-engineering-only','-DevBranch','integration') 0
    Check dev @() 1
    foreach ($scope in @('power-bi','other','mixed','unknown')) { Check dev @('-Scope',$scope,'-DevBranch','dev') 1 }
    Check dev @('-Scope','fabric-data-engineering-only') 1
    Check dev @('-Scope','fabric-data-engineering-only','-DevBranch','bad name') 1
    foreach ($branch in @('main','master','prod','production','test')) { Check $branch @('-Scope','fabric-data-engineering-only','-DevBranch',$branch) 1 }
    Check dev @('-Scope','fabric-data-engineering-only','-DevBranch','integration') 1
    Check feature/FIN-123-example @() 0
    Check bugfix/FIN-123-example @('-Scope','mixed') 0
    Check bugfix/FIN-123-example @('-Scope','mixed','-WorkType','bug','-Ticket','FIN-123') 0
    Check feature/fin-123-example @() 1
    Check feature/no-ticket @() 1
    Check other/FIN-123 @() 1
    git checkout -q --detach
    & powershell -NoProfile -File $guard -Scope fabric-data-engineering-only -DevBranch dev *> $null
    if ($LASTEXITCODE -ne 1) { throw 'Detached HEAD did not fail' }
    New-Item -ItemType Directory -Force '.claude-plugin', 'plugins/devops/skills/git-branch-guard' | Out-Null
    New-Item -ItemType File '.claude-plugin/marketplace.json', 'plugins/devops/skills/git-branch-guard/check_git_branch_guard.ps1' | Out-Null
    Check dev @('-Scope','fabric-data-engineering-only','-DevBranch','dev') 1
    Pop-Location
    Push-Location $base
    # The guard intentionally writes Git's error to stderr here. Windows
    # PowerShell treats redirected native stderr as an error when preference is
    # Stop, so capture the exit code under Continue for this negative case.
    $ErrorActionPreference = 'Continue'
    & powershell -NoProfile -File $guard -Scope fabric-data-engineering-only -DevBranch dev *> $null
    $ErrorActionPreference = 'Stop'
    if ($LASTEXITCODE -ne 1) { throw 'Git error did not fail' }
    Write-Host 'Branch guard isolated tests passed.'
} finally {
    Pop-Location
    if ((Split-Path $root -Parent) -eq $base) { Remove-Item -LiteralPath $root -Recurse -Force }
}
