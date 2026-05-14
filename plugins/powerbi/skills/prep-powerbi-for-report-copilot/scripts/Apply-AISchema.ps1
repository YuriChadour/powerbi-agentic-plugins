# Apply-AISchema.ps1
# Read ai-schema.csv and apply Visibility settings to IAM_FIELD_MAPPING.SemanticModel/definition/cultures/en-US.tmdl
# This script is idempotent and can be re-run safely.
# Usage: .\Apply-AISchema.ps1 -SemanticModelPath "path\to\IAM_FIELD_MAPPING.SemanticModel" -CSVPath "documentation\copilot\ai-schema.csv"

param(
    [string]$SemanticModelPath = "IAM_FIELD_MAPPING.SemanticModel",
    [string]$CSVPath = "documentation/copilot/ai-schema.csv"
)

# Validate inputs
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

# Load TMDL file
$tmdlContent = Get-Content $tmdlFile -Raw

# Create a map of desired visibility by entity key
$desiredVisibility = @{}
foreach ($row in $csvData) {
    $entityKey = $row.EntityKey.Trim('"')
    $visibility = $row.Visibility.Trim('"')
    $desiredVisibility[$entityKey] = $visibility
}

Write-Host "Processing $($desiredVisibility.Count) entities from CSV"

# Track changes
$changeLog = @()
$changedCount = 0
$sameCount = 0
$notFoundCount = 0

# For each entity, find and replace its Visibility value
foreach ($entityKey in $desiredVisibility.Keys) {
    $newVisibility = $desiredVisibility[$entityKey]
    
    # Find the entity block using a pattern that handles multiline content
    # Look for: "entityKey": { ... "Value": "OldValue" ... }
    # We need to find just the Visibility.Value that belongs to this specific entity
    
    $entityQuoted = [regex]::Escape("`"$entityKey`"")
    
    # Find the entity block start
    $pattern = $entityQuoted + ':\s*\{'
    if ($tmdlContent -match $pattern) {
        # Find the position of this entity
        $entityPos = $tmdlContent.IndexOf("`"$entityKey`":")
        if ($entityPos -ge 0) {
            # Find the closing brace of this entity block (simplified approach)
            # We'll look for the "Visibility" section within the next few hundred characters
            $searchWindow = $tmdlContent.Substring($entityPos, [Math]::Min(1000, $tmdlContent.Length - $entityPos))
            
            # Find Visibility Value in this window
            if ($searchWindow -match '"Visibility":\s*\{\s*"Value":\s*"([^"]+)"') {
                $currentValue = $matches[1]
                
                if ($currentValue -ne $newVisibility) {
                    # Need to replace this specific occurrence
                    # Find the exact string to replace in the full content
                    $oldPattern = '("' + $entityKey + '":\s*\{[^}]*"Visibility":\s*\{\s*"Value":\s*)"' + $currentValue + '"'
                    $newPattern = '$1"' + $newVisibility + '"'
                    
                    $beforeLength = $tmdlContent.Length
                    $tmdlContent = $tmdlContent -replace $oldPattern, $newPattern
                    $afterLength = $tmdlContent.Length
                    
                    if ($afterLength -ne $beforeLength) {
                        $changeLog += @{
                            EntityKey = $entityKey
                            OldValue = $currentValue
                            NewValue = $newVisibility
                            Status = "Updated"
                        }
                        $changedCount++
                    } else {
                        $notFoundCount++
                    }
                } else {
                    $sameCount++
                }
            } else {
                $notFoundCount++
            }
        } else {
            $notFoundCount++
        }
    } else {
        $notFoundCount++
    }
}

# Write the updated TMDL file back
Set-Content $tmdlFile $tmdlContent -Encoding UTF8
Write-Host "`nApplied changes to en-US.tmdl"

# Verification
$visibleMatches = [regex]::Matches($tmdlContent, '"Value":\s*"Visible"').Count
$hiddenMatches = [regex]::Matches($tmdlContent, '"Value":\s*"Hidden"').Count

Write-Host "`nVerification Results:"
Write-Host "  Changed: $changedCount"
Write-Host "  Already correct: $sameCount"
Write-Host "  Not found or error: $notFoundCount"
Write-Host "  Total Visible entries in file: $visibleMatches"
Write-Host "  Total Hidden entries in file: $hiddenMatches"

# Show sample of changes
if ($changeLog.Count -gt 0) {
    Write-Host "`nSample of changes (first 20):"
    $changeLog | Select-Object -First 20 | ForEach-Object {
        Write-Host "  [$($_.Status)] EntityKey: $($_.EntityKey) - $($_.OldValue) -> $($_.NewValue)"
    }
    
    if ($changeLog.Count -gt 20) {
        Write-Host "  ... and $($changeLog.Count - 20) more changes"
    }
} else {
    Write-Host "`nNo changes were needed."
}

Write-Host "`nDone! en-US.tmdl has been updated."
Write-Host "Next: Verify the changes in Power BI Desktop or commit to Fabric."
