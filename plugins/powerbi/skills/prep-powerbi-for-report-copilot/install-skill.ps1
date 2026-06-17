# install-skill.ps1
# Installer for prep-powerbi-for-report-copilot skill
# Downloads and installs the skill into the Copilot CLI extensions directory

param(
    [switch]$Force,
    [string]$SkillVersion = "main"
)

# Run with a process-scoped bypass so the installer works without changing user policy.
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Detect OS
if ($PSVersionTable.Platform -ne "Win32NT" -and $PSVersionTable.PSVersion.Major -lt 7) {
    Write-Host "❌ This installer requires PowerShell 7.0+ or Windows PowerShell on Windows." -ForegroundColor Red
    exit 1
}

# Check PowerShell version
$psVersion = $PSVersionTable.PSVersion
if ($psVersion.Major -lt 7) {
    Write-Host "⚠️  PowerShell 7.0+ recommended for best compatibility" -ForegroundColor Yellow
    Write-Host "   Current: $($psVersion.Major).$($psVersion.Minor)" -ForegroundColor Yellow
}

Write-Host "`n📦 Installing prep-powerbi-for-report-copilot skill..." -ForegroundColor Cyan

# Determine Copilot CLI extensions directory
$CopilotHome = if ($env:COPILOT_HOME) { $env:COPILOT_HOME } else { "$env:USERPROFILE\.copilot" }
$ExtensionsDir = Join-Path $CopilotHome "extensions"
$SkillDir = Join-Path $ExtensionsDir "prep-powerbi-for-report-copilot"

Write-Host "  Extensions directory: $ExtensionsDir" -ForegroundColor Gray

# Create extensions directory if needed
if (-not (Test-Path $ExtensionsDir)) {
    Write-Host "  Creating extensions directory..." -ForegroundColor Gray
    New-Item -ItemType Directory -Path $ExtensionsDir -Force | Out-Null
}

# Check if skill already installed
if ((Test-Path $SkillDir) -and -not $Force) {
    Write-Host "⚠️  Skill already installed at: $SkillDir" -ForegroundColor Yellow
    $response = Read-Host "  Reinstall? (y/n) [n]"
    if ($response -ne "y") {
        Write-Host "✓ Installation cancelled." -ForegroundColor Yellow
        exit 0
    }
}

# Remove existing if force flag
if ($Force -and (Test-Path $SkillDir)) {
    Write-Host "  Removing existing installation..." -ForegroundColor Gray
    Remove-Item -Path $SkillDir -Recurse -Force
}

# Download from GitHub
$repoUrl = "https://github.com/bayviewasset/prep-powerbi-for-report-copilot"
$downloadUrl = "$repoUrl/archive/$SkillVersion.zip"
$tempZip = Join-Path $env:TEMP "prep-powerbi-copilot-$SkillVersion.zip"
$tempExtract = Join-Path $env:TEMP "prep-powerbi-copilot-extract"

try {
    Write-Host "  Downloading skill from GitHub..." -ForegroundColor Gray
    
    # Download with progress bar
    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $downloadUrl -OutFile $tempZip -ErrorAction Stop
    }
    catch {
        Write-Host "❌ Failed to download from $downloadUrl" -ForegroundColor Red
        Write-Host "   Error: $_" -ForegroundColor Red
        Write-Host "`n   Alternative: Clone manually:" -ForegroundColor Yellow
        Write-Host "   git clone $repoUrl $SkillDir" -ForegroundColor Gray
        exit 1
    }
    
    Write-Host "  Extracting files..." -ForegroundColor Gray
    
    # Expand zip
    if (Test-Path $tempExtract) {
        Remove-Item $tempExtract -Recurse -Force
    }
    Expand-Archive -Path $tempZip -DestinationPath $tempExtract -Force
    
    # Copy to extensions (GitHub archive creates a subfolder like "prep-powerbi-for-report-copilot-main")
    $extractedFolder = Get-ChildItem $tempExtract -Directory | Select-Object -First 1
    if ($null -eq $extractedFolder) {
        Write-Host "❌ Failed to extract archive" -ForegroundColor Red
        exit 1
    }
    
    Copy-Item -Path $extractedFolder.FullName -Destination $SkillDir -Recurse -Force
    
    Write-Host "  Validating installation..." -ForegroundColor Gray
    
    # Verify key files exist
    $requiredFiles = @(
        "SKILL.md",
        "scripts/Generate-AISchema.ps1",
        "scripts/Apply-AISchema-v2.ps1"
    )
    
    $allPresent = $true
    foreach ($file in $requiredFiles) {
        $filePath = Join-Path $SkillDir $file
        if (-not (Test-Path $filePath)) {
            Write-Host "❌ Missing: $file" -ForegroundColor Red
            $allPresent = $false
        }
    }
    
    if (-not $allPresent) {
        Write-Host "❌ Installation incomplete" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "`n✓ Installation successful!" -ForegroundColor Green
    Write-Host "  Installed to: $SkillDir" -ForegroundColor Green
    
    # Next steps
    Write-Host "`n📖 Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Start Copilot CLI in your Power BI repo:" -ForegroundColor Gray
    Write-Host "     cd C:\your\powerbi\repo" -ForegroundColor Gray
    Write-Host "     copilot" -ForegroundColor Gray
    Write-Host "`n  2. Invoke the skill:" -ForegroundColor Gray
    Write-Host "     /skill prep-powerbi-for-report-copilot" -ForegroundColor Gray
    Write-Host "`n  3. Read the full workflow:" -ForegroundColor Gray
    Write-Host "     cat $SkillDir\SKILL.md" -ForegroundColor Gray
    Write-Host "`n  4. Or view the quick-start guide:" -ForegroundColor Gray
    Write-Host "     Get-Content $SkillDir\docs\QUICKSTART.md" -ForegroundColor Gray
    
    # Check for Python (optional)
    $pythonAvailable = $false
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "3\.\d+") {
            $pythonAvailable = $true
            Write-Host "`n✓ Python 3+ detected: $pythonVersion" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "`n⚠️  Python 3.8+ not found (optional)" -ForegroundColor Yellow
        Write-Host "   Some diagnostic parsing features require Python." -ForegroundColor Yellow
        Write-Host "   Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "❌ Installation failed: $_" -ForegroundColor Red
    exit 1
}
finally {
    # Cleanup
    if (Test-Path $tempZip) {
        Remove-Item $tempZip -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $tempExtract) {
        Remove-Item $tempExtract -Recurse -Force -ErrorAction SilentlyContinue
    }
}

exit 0
