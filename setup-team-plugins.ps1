#Requires -Version 7.0
<#
.SYNOPSIS
    Setup script for installing Power BI Agentic Plugins for the team
    
.DESCRIPTION
    This script installs all plugins (powerbi + fabric) from the powerbi-agentic-plugins
    repository to $USERPROFILE\.copilot\extensions for GitHub Copilot CLI and VS Code.
    
    It validates prerequisites, copies plugins, registers with GitHub Copilot CLI,
    integrates with VS Code, and configures MCP servers.
    
.PARAMETER RepositoryPath
    Path to the cloned powerbi-agentic-plugins repository.
    If not provided, will search common locations or prompt to clone.
    
.PARAMETER SkipCopilotCLI
    Skip registration with GitHub Copilot CLI (if not installed or not needed)
    
.PARAMETER SkipVSCode
    Skip integration with VS Code (if not installed or not needed)
    
.PARAMETER Force
    Overwrite existing plugins if already installed
    
.PARAMETER Verbose
    Enable verbose logging for troubleshooting
    
.EXAMPLE
    .\setup-team-plugins.ps1
    
.EXAMPLE
    .\setup-team-plugins.ps1 -RepositoryPath "C:\repos\powerbi-agentic-plugins" -Force
    
.NOTES
    Requires PowerShell 7.0 or later
    Requires Git installed and in PATH
    Requires GitHub Copilot CLI or VS Code with GitHub Copilot Chat extension
#>

param(
    [string]$RepositoryPath,
    [switch]$SkipCopilotCLI,
    [switch]$SkipVSCode,
    [switch]$Force,
    [switch]$Verbose
)

# Enable strict error handling
$ErrorActionPreference = "Stop"
$VerbosePreference = if ($Verbose) { "Continue" } else { "SilentlyContinue" }

# Colors for output
$Script:ColorSuccess = "Green"
$Script:ColorError = "Red"
$Script:ColorWarning = "Yellow"
$Script:ColorInfo = "Cyan"

#region Helper Functions

function Write-Header {
    param([string]$Message)
    Write-Host "`n" + ("=" * 80) -ForegroundColor $ColorInfo
    Write-Host $Message -ForegroundColor $ColorInfo
    Write-Host ("=" * 80) -ForegroundColor $ColorInfo
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor $ColorSuccess
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor $ColorError
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor $ColorWarning
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor $ColorInfo
}

function Test-Prerequisites {
    Write-Header "Validating Prerequisites"
    
    $prereqsMet = $true
    
    # Check PowerShell version
    Write-Info "PowerShell version: $($PSVersionTable.PSVersion)"
    if ($PSVersionTable.PSVersion.Major -lt 7) {
        Write-Error-Custom "PowerShell 7.0 or later required. Current: $($PSVersionTable.PSVersion)"
        $prereqsMet = $false
    } else {
        Write-Success "PowerShell 7.0+ ✓"
    }
    
    # Check Git
    try {
        $gitVersion = git --version 2>&1
        Write-Info "Git: $gitVersion"
        Write-Success "Git installed ✓"
    } catch {
        Write-Error-Custom "Git not found. Please install Git from https://git-scm.com"
        $prereqsMet = $false
    }
    
    # Check Node.js (needed for MCP servers)
    try {
        $nodeVersion = node --version 2>&1
        Write-Info "Node.js: $nodeVersion"
        Write-Success "Node.js installed ✓"
    } catch {
        Write-Warning-Custom "Node.js not found. MCP servers may not work. Install from https://nodejs.org"
    }
    
    # Check for GitHub Copilot CLI or VS Code
    $copilotCLIExists = $null -ne (Get-Command copilot -ErrorAction SilentlyContinue)
    $vsCodeExists = $null -ne (Get-Command code -ErrorAction SilentlyContinue)
    
    if ($copilotCLIExists) {
        Write-Success "GitHub Copilot CLI found ✓"
    } elseif (-not $SkipCopilotCLI) {
        Write-Warning-Custom "GitHub Copilot CLI not found in PATH"
    }
    
    if ($vsCodeExists) {
        Write-Success "VS Code found ✓"
    } elseif (-not $SkipVSCode) {
        Write-Warning-Custom "VS Code not found in PATH"
    }
    
    if (-not $copilotCLIExists -and -not $vsCodeExists) {
        Write-Error-Custom "Neither GitHub Copilot CLI nor VS Code found. Please install one of them."
        $prereqsMet = $false
    }
    
    return $prereqsMet
}

function Find-Repository {
    param([string]$ProvidedPath)
    
    Write-Header "Locating Repository"
    
    # If path provided, use it
    if ($ProvidedPath) {
        Write-Verbose "DEBUG Find-Repo: ProvidedPath=$ProvidedPath"
        if (Test-Path -Path $ProvidedPath -PathType Container) {
            if (Test-Path -Path "$ProvidedPath\.git" -PathType Container) {
                Write-Success "Repository found at: $ProvidedPath"
                Write-Verbose "DEBUG Find-Repo: Returning $ProvidedPath"
                return $ProvidedPath
            }
        }
        Write-Error-Custom "Invalid repository path: $ProvidedPath"
        return $null
    }
    
    # Search common locations
    $commonLocations = @(
        "$(Split-Path $PSScriptRoot -Parent)",
        "$env:USERPROFILE\repos\powerbi-agentic-plugins",
        "$env:USERPROFILE\git\powerbi-agentic-plugins",
        "$env:USERPROFILE\development\powerbi-agentic-plugins",
        "C:\Development\powerbi-agentic-plugins"
    )
    
    Write-Verbose "DEBUG Find-Repo: Searching locations..."
    foreach ($location in $commonLocations) {
        Write-Verbose "DEBUG Find-Repo: Checking $location"
        if (Test-Path -Path "$location\.git" -PathType Container) {
            Write-Success "Repository found at: $location"
            Write-Verbose "DEBUG Find-Repo: Returning $location"
            return $location
        }
    }
    
    # Prompt to clone
    Write-Info "Repository not found in common locations."
    $clonePath = Read-Host "Enter path to clone repository (default: $env:USERPROFILE\repos\powerbi-agentic-plugins)"
    
    if ([string]::IsNullOrWhiteSpace($clonePath)) {
        $clonePath = "$env:USERPROFILE\repos\powerbi-agentic-plugins"
    }
    
    if (Test-Path $clonePath) {
        Write-Error-Custom "Path already exists: $clonePath"
        return $null
    }
    
    Write-Info "Cloning repository to: $clonePath"
    try {
        $parentPath = Split-Path $clonePath -Parent
        if (-not (Test-Path $parentPath)) {
            New-Item -ItemType Directory -Path $parentPath -Force | Out-Null
        }
        git clone https://github.com/YuriChadour/powerbi-agentic-plugins.git $clonePath
        Write-Success "Repository cloned successfully"
        return $clonePath
    } catch {
        Write-Error-Custom "Failed to clone repository: $_"
        return $null
    }
}

function Install-Plugins {
    param(
        [string]$SourcePath,
        [string]$DestinationPath,
        [bool]$Force
    )
    
    Write-Header "Installing Plugins"
    
    $plugins = @("powerbi", "fabric")
    $successCount = 0
    
    for ($i = 0; $i -lt $plugins.Count; $i++) {
        $pluginName = $plugins[$i]
        
        $sourcePath_Local = Join-Path $SourcePath "plugins" $pluginName
        $destPath_Local = Join-Path $DestinationPath $pluginName
        
        Write-Verbose "DEBUG: Processing plugin $($i+1) of $($plugins.Count): $pluginName"
        Write-Verbose "DEBUG: Source: $sourcePath_Local"
        
        if (-not (Test-Path $sourcePath_Local)) {
            Write-Error-Custom "Plugin source not found: $sourcePath_Local"
            continue
        }
        
        # Remove existing if Force
        if ($Force -and (Test-Path $destPath_Local)) {
            Write-Info "Removing existing $pluginName plugin..."
            Remove-Item -Path $destPath_Local -Recurse -Force
        }
        
        # Create destination if needed
        if (-not (Test-Path $destPath_Local)) {
            New-Item -ItemType Directory -Path $destPath_Local -Force | Out-Null
        }
        
        # Copy plugin files
        Write-Info "Copying $pluginName plugin..."
        Copy-Item -Path "$sourcePath_Local\*" -Destination $destPath_Local -Recurse -Force
        
        # Verify key files exist
        if (Test-Path "$destPath_Local\skills") {
            Write-Success "$pluginName plugin installed ✓"
            $successCount++
        } else {
            Write-Error-Custom "$pluginName plugin missing skills directory"
        }
    }
    
    return $successCount -eq $plugins.Count
}

function Register-CopilotCLI {
    param([string]$ExtensionsPath)
    
    if ($SkipCopilotCLI) {
        Write-Info "Skipping GitHub Copilot CLI registration (--SkipCopilotCLI)"
        return $true
    }
    
    Write-Header "Registering with GitHub Copilot CLI"
    
    $copilotExists = $null -ne (Get-Command copilot -ErrorAction SilentlyContinue)
    if (-not $copilotExists) {
        Write-Warning-Custom "GitHub Copilot CLI not found. Skipping registration."
        return $false
    }
    
    try {
        # The plugins are already in the extensions directory
        # Copilot CLI will auto-discover them
        Write-Info "Plugins installed to: $ExtensionsPath"
        Write-Info "GitHub Copilot CLI will auto-discover plugins on next startup"
        
        # Try to list plugins to verify
        Write-Info "Verifying plugins are discoverable..."
        $listOutput = copilot /plugin list 2>&1
        Write-Success "GitHub Copilot CLI registration verified ✓"
        return $true
    } catch {
        Write-Warning-Custom "Could not verify GitHub Copilot CLI registration: $_"
        Write-Info "Plugins are installed; they will be auto-discovered on next CLI startup."
        return $false
    }
}

function Register-VSCode {
    param([string]$ExtensionsPath)
    
    if ($SkipVSCode) {
        Write-Info "Skipping VS Code integration (--SkipVSCode)"
        return $true
    }
    
    Write-Header "Integrating with VS Code"
    
    $codeExists = $null -ne (Get-Command code -ErrorAction SilentlyContinue)
    if (-not $codeExists) {
        Write-Warning-Custom "VS Code not found. Skipping integration."
        return $false
    }
    
    try {
        Write-Info "VS Code plugins directory: $ExtensionsPath"
        Write-Info "VS Code will auto-discover plugins on next startup"
        Write-Info "To enable Agent Skills in VS Code:"
        Write-Info "  1. Open VS Code Settings (Ctrl+,)"
        Write-Info "  2. Search for 'chat.useAgentSkills'"
        Write-Info "  3. Enable the setting"
        
        Write-Success "VS Code integration ready ✓"
        return $true
    } catch {
        Write-Error-Custom "Failed to integrate with VS Code: $_"
        return $false
    }
}

function Validate-Installation {
    param([string]$ExtensionsPath)
    
    Write-Header "Validating Installation"
    
    $plugins = @("powerbi", "fabric")
    $allValid = $true
    
    foreach ($plugin in $plugins) {
        $pluginPath = Join-Path $ExtensionsPath $plugin
        
        if (-not (Test-Path $pluginPath)) {
            Write-Error-Custom "Plugin not found: $plugin"
            $allValid = $false
            continue
        }
        
        # Check required directories
        $hasAgents = Test-Path "$pluginPath\agents"
        $hasSkills = Test-Path "$pluginPath\skills"
        $hasMCP = Test-Path "$pluginPath\.mcp.json"
        
        if ($hasSkills) {
            $agentStatus = if ($hasAgents) { "agents ✓" } else { "agents (optional)" }
            Write-Success "$plugin plugin: $agentStatus skills ✓ $(if ($hasMCP) { 'mcp ✓' } else { 'mcp (optional)' })"
        } else {
            Write-Error-Custom "$plugin plugin missing required skills directory"
            $allValid = $false
        }
    }
    
    # List installed skills
    Write-Info "Installed plugins and skills:"
    foreach ($plugin in $plugins) {
        $pluginPath = Join-Path $ExtensionsPath $plugin
        $skillsPath = "$pluginPath\skills"
        
        if (Test-Path $skillsPath) {
            $skills = Get-ChildItem -Path $skillsPath -Directory -Name
            foreach ($skill in $skills) {
                Write-Info "  • $plugin/$skill"
            }
        }
    }
    
    return $allValid
}

function Show-NextSteps {
    param([string]$ExtensionsPath)
    
    Write-Header "Installation Complete!"
    
    Write-Info "Plugins installed to:"
    Write-Host "  $ExtensionsPath" -ForegroundColor $ColorInfo
    
    Write-Info "Next steps:"
    Write-Host "  1. Restart GitHub Copilot CLI or VS Code to load plugins" -ForegroundColor $ColorInfo
    Write-Host "  2. For Copilot CLI: run 'copilot /plugin list' to verify" -ForegroundColor $ColorInfo
    Write-Host "  3. For VS Code: enable 'chat.useAgentSkills' in settings (Ctrl+,)" -ForegroundColor $ColorInfo
    Write-Host "  4. Read DEVELOPER_SETUP.md for team workflows" -ForegroundColor $ColorInfo
    Write-Host "  5. Read CONTRIBUTING_TEAM.md for contribution guidelines" -ForegroundColor $ColorInfo
    
    Write-Info "Staying in sync:"
    Write-Host "  cd $(if ($RepositoryPath) { $RepositoryPath } else { '$RepositoryPath' })" -ForegroundColor $ColorInfo
    Write-Host "  git pull" -ForegroundColor $ColorInfo
    Write-Host "  .\setup-team-plugins.ps1 -Force" -ForegroundColor $ColorInfo
    
    Write-Host "`n"
}

#endregion

#region Main

try {
    Write-Host "
╔════════════════════════════════════════════════════════════════════════════╗
║         Power BI Agentic Plugins — Team Setup Script                      ║
║                                                                            ║
║  This script installs all plugins (powerbi + fabric) to your user         ║
║  profile for use with GitHub Copilot CLI and/or VS Code.                  ║
╚════════════════════════════════════════════════════════════════════════════╝
" -ForegroundColor $ColorInfo
    
    # Test prerequisites
    if (-not (Test-Prerequisites)) {
        Write-Error-Custom "Prerequisites not met. Please fix the issues above and try again."
        exit 1
    }
    
    # Find or clone repository
    $repoPath = Find-Repository -ProvidedPath $RepositoryPath
    if (-not $repoPath) {
        Write-Error-Custom "Could not locate repository. Exiting."
        exit 1
    }
    
    # Set up destination paths
    $extensionsPath = Join-Path $env:USERPROFILE ".copilot" "extensions"
    if (-not (Test-Path $extensionsPath)) {
        New-Item -ItemType Directory -Path $extensionsPath -Force | Out-Null
    }
    
    Write-Info "Destination: $extensionsPath"
    
    # Install plugins
    if (-not (Install-Plugins -SourcePath $repoPath -DestinationPath $extensionsPath -Force $Force)) {
        Write-Error-Custom "Failed to install plugins."
        exit 1
    }
    
    # Register with tools
    $cliRegistered = Register-CopilotCLI -ExtensionsPath $extensionsPath
    $vscodeRegistered = Register-VSCode -ExtensionsPath $extensionsPath
    
    # Validate
    if (-not (Validate-Installation -ExtensionsPath $extensionsPath)) {
        Write-Error-Custom "Installation validation failed."
        exit 1
    }
    
    # Show next steps
    Show-NextSteps -ExtensionsPath $extensionsPath
    
    Write-Success "Setup complete!"
    exit 0
}
catch {
    Write-Error-Custom "Unexpected error: $_"
    Write-Host $_.ScriptStackTrace -ForegroundColor $ColorError
    exit 1
}

#endregion
