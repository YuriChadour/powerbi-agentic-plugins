# Apply-AISchema-v2.ps1 (improved version)
# Read ai-schema.csv and apply Visibility settings to en-US.tmdl using a more robust approach
# Usage: .\Apply-AISchema-v2.ps1 -SemanticModelPath "path\to\IAM_FIELD_MAPPING.SemanticModel" -CSVPath "documentation\copilot\ai-schema.csv"

param(
    [string]$SemanticModelPath = "IAM_FIELD_MAPPING.SemanticModel",
    [string]$CSVPath = "documentation/copilot/ai-schema.csv"
)

if (-not (Test-Path $CSVPath)) {
    Write-Error "Cannot find ai-schema.csv at: $CSVPath"
    exit 1
}

$tmdlFile = Join-Path $SemanticModelPath "definition\cultures\en-US.tmdl"
if (-not (Test-Path $tmdlFile)) {
    Write-Error "Cannot find en-US.tmdl at: $tmdlFile"
    exit 1
}

Write-Host "Reading configuration from: $CSVPath"
Write-Host "Applying to: $tmdlFile"

# Read CSV
$csvData = Import-Csv $CSVPath

# Load TMDL file as lines for reliable line-by-line processing
$lines = @(Get-Content $tmdlFile)

# Create a map of desired visibility by entity key
$desiredVisibility = @{}
foreach ($row in $csvData) {
    $entityKey = $row.EntityKey.Trim('"')
    $visibility = $row.Visibility.Trim('"')
    $desiredVisibility[$entityKey] = $visibility
}

Write-Host "Processing $($desiredVisibility.Count) entities from CSV`n"

# Track changes
$changeLog = @()
$changedCount = 0
$sameCount = 0
$notFoundCount = 0

# Process each desired entity
foreach ($entityKey in $desiredVisibility.Keys) {
    $newVisibility = $desiredVisibility[$entityKey]
    $searchStr = "`"$entityKey`":"
    $found = $false
    
    # Find the line with this entity key
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].IndexOf($searchStr) -ge 0) {
            # Found the entity, now search for the Value line within the next 20 lines
            for ($j = $i + 1; $j -lt [Math]::Min($i + 20, $lines.Count); $j++) {
                if ($lines[$j] -match '"Value":\s*"([^"]+)"'){
                    $currentValue = $matches[1]
                    
                    if ($currentValue -ne $newVisibility) {
                        # Replace the line
                        $lines[$j] = $lines[$j] -replace '"Value":\s*"[^"]+"', "`"Value`": `"$newVisibility`""
                        
                        $changeLog += @{
                            EntityKey = $entityKey
                            OldValue = $currentValue
                            NewValue = $newVisibility
                            Status = "Updated"
                        }
                        $changedCount++
                    } else {
                        $sameCount++
                    }
                    
                    $found = $true
                    break
                }
                
                # Stop searching if we hit Terms section
                if ($lines[$j] -match '"Terms":'){
                    break
                }
            }
            
            if ($found) {
                break
            }
        }
    }
    
    if (-not $found) {
        $notFoundCount++
    }
}

# Write the updated TMDL file back
$lines | Set-Content $tmdlFile -Encoding UTF8
Write-Host "Applied changes to en-US.tmdl`n"

# Verification
$content = Get-Content $tmdlFile -Raw
$visibleMatches = ([regex]::Matches($content, '"Value":\s*"Visible"')).Count
$hiddenMatches = ([regex]::Matches($content, '"Value":\s*"Hidden"')).Count

Write-Host "Verification Results:"
Write-Host "  Changed: $changedCount"
Write-Host "  Already correct: $sameCount"
Write-Host "  Not found: $notFoundCount"
Write-Host "  Total Visible entries in file: $visibleMatches"
Write-Host "  Total Hidden entries in file: $hiddenMatches"

# Show sample of changes
if ($changeLog.Count -gt 0) {
    Write-Host "`nSample of changes (first 20):"
    $changeLog | Select-Object -First 20 | ForEach-Object {
        Write-Host "  [$($_.Status)] $($_.EntityKey): $($_.OldValue) -> $($_.NewValue)"
    }
    
    if ($changeLog.Count -gt 20) {
        Write-Host "  ... and $($changeLog.Count - 20) more changes"
    }
} else {
    Write-Host "`nNo changes were needed (all entities already have correct visibility)."
}

Write-Host "`nDone! en-US.tmdl has been updated."
Write-Host "Next: Verify the changes in Power BI Desktop or commit to Fabric."
