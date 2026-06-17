# Generate-AISchema.ps1
# Extract measures from both _Measures.tmdl displayFolders and entity keys from en-US.tmdl, then generate ai-schema.csv
# Usage: .\Generate-AISchema.ps1 -SemanticModelPath "path\to\IAM_FIELD_MAPPING.SemanticModel" -OutputPath "documentation\copilot\ai-schema.csv"

param(
    [string]$SemanticModelPath = "IAM_FIELD_MAPPING.SemanticModel",
    [string]$OutputPath = "documentation/copilot/ai-schema.csv"
)

# Run with a process-scoped bypass so helper scripts work without policy changes.
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force

# Default inclusion rules based on displayFolder
$includeDisplayFolders = @("Standard", "PM", "MoM", "Delinquency")
$excludeDisplayFolders = @("Visual", "Visual\SVG", "Reference", "Reference for Table", "Tolerance", "Signal", "Narrative", "Utility")

# Function to determine visibility default
function Get-DefaultVisibility {
    param(
        [string]$DisplayFolder,
        [string]$MeasureName
    )
    
    # Check exclusions first
    foreach ($excludeFolder in $excludeDisplayFolders) {
        if ($DisplayFolder -eq $excludeFolder) {
            return "Hidden"
        }
    }
    
    # Check inclusions
    foreach ($includeFolder in $includeDisplayFolders) {
        if ($DisplayFolder -eq $includeFolder) {
            return "Visible"
        }
    }
    
    # Default to Hidden if not in any rule
    return "Hidden"
}

function Get-Reason {
    param(
        [string]$DisplayFolder,
        [string]$Visibility
    )
    
    if ($Visibility -eq "Hidden") {
        if ($excludeDisplayFolders -contains $DisplayFolder) {
            return "In exclude list: $DisplayFolder"
        } else {
            return "Not in include list"
        }
    } else {
        return "In include list: $DisplayFolder"
    }
}

# Step 1: Extract measures from _Measures.tmdl (to get displayFolders)
$measuresFile = Join-Path $SemanticModelPath "definition\tables\_Measures.tmdl"

if (-not (Test-Path $measuresFile)) {
    Write-Error "Cannot find _Measures.tmdl at: $measuresFile"
    exit 1
}

Write-Host "Step 1: Reading measures and displayFolders from: $measuresFile"

$measuresContent = Get-Content $measuresFile -Raw
$measuresByDisplayName = @{}

# Parse measures and display folders
$measurePattern = "measure '([^']+)'[^`n]*`n(?:[^`n]*`n)*?\s+displayFolder: (\S+)"
$matches = [regex]::Matches($measuresContent, $measurePattern)

foreach ($match in $matches) {
    $displayName = $match.Groups[1].Value
    $displayFolder = $match.Groups[2].Value
    $measuresByDisplayName[$displayName] = $displayFolder
}

Write-Host "  Found $($measuresByDisplayName.Count) measures with displayFolders"

# Step 2: Extract entity keys from en-US.tmdl
Write-Host "Step 2: Reading entity keys from en-US.tmdl..."

$enUSFile = Join-Path $SemanticModelPath "definition\cultures\en-US.tmdl"
if (-not (Test-Path $enUSFile)) {
    Write-Error "Cannot find en-US.tmdl at: $enUSFile"
    exit 1
}

$enUSContent = Get-Content $enUSFile -Raw
$measures = @()

# Use multiline mode for regex
# Pattern: "entity__measure.XXX": { ... "ConceptualProperty": "Display Name" ... "Value": "Visible"|"Hidden" }
$entityPattern = '"(entity__measure\.[^"]+)":\s*\{.*?"ConceptualProperty":\s*"([^"]+)".*?"Value":\s*"([^"]+)"'
$entityMatches = [regex]::Matches($enUSContent, $entityPattern, [System.Text.RegularExpressions.RegexOptions]::Singleline)

foreach ($entityMatch in $entityMatches) {
    $entityKey = $entityMatch.Groups[1].Value
    $displayName = $entityMatch.Groups[2].Value
    $currentVisibility = $entityMatch.Groups[3].Value
    
    # Skip the generic "Value" and "value" properties (not actual measures)
    if ($displayName -eq "Value" -or $displayName -eq "value") {
        continue
    }
    
    # Look up displayFolder
    $displayFolder = $measuresByDisplayName[$displayName]
    if ([string]::IsNullOrWhiteSpace($displayFolder)) {
        $displayFolder = "Unknown"
    }
    
    $visibility = Get-DefaultVisibility -DisplayFolder $displayFolder -MeasureName $displayName
    $reason = Get-Reason -DisplayFolder $displayFolder -Visibility $visibility
    
    $measures += @{
        EntityKey = $entityKey
        DisplayName = $displayName
        DisplayFolder = $displayFolder
        Visibility = $visibility
        Reason = $reason
    }
}

Write-Host "  Found $($measures.Count) entity keys in en-US.tmdl"

# Build output data
$allItems = $measures | Sort-Object EntityKey

# Create CSV output
$csvData = @()
$csvData += "EntityKey,DisplayName,DisplayFolder,Visibility,Reason"

foreach ($item in $allItems) {
    $line = "`"$($item.EntityKey)`",`"$($item.DisplayName)`",`"$($item.DisplayFolder)`",`"$($item.Visibility)`",`"$($item.Reason)`""
    $csvData += $line
}

# Ensure output directory exists
$outputDir = Split-Path -Parent $OutputPath
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# Write CSV file
$csvData | Set-Content $OutputPath -Encoding UTF8
Write-Host "`nGenerated ai-schema.csv at: $OutputPath"

# Summary statistics
$visibleCount = ($csvData | Select-String '"Visible"' | Measure-Object).Count
$hiddenCount = ($csvData | Select-String '"Hidden"' | Measure-Object).Count

Write-Host "`nSummary:"
Write-Host "  Total items: $($allItems.Count)"
Write-Host "  Visible: $visibleCount"
Write-Host "  Hidden: $hiddenCount"
Write-Host "`nReview the CSV at: $OutputPath"
Write-Host "Edit as needed, then run Apply-AISchema.ps1 to update en-US.tmdl"
