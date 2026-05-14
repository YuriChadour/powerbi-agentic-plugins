#Requires -Version 5.0
<#
.SYNOPSIS
    Clean up TMDL/JSON files after editing by removing UTF-8 BOM.

.DESCRIPTION
    Convenience wrapper that removes UTF-8 BOM from TMDL and JSON files
    after manual edits to ensure clean encoding.

.PARAMETER SemanticModelPath
    Path to the semantic model definition folder (e.g., "IAM_FIELD_MAPPING.SemanticModel\definition")

.PARAMETER ReportPath
    Path to the report definition folder (e.g., "IAM Portfolio Surverillance.Report\definition")

.PARAMETER CleanBoth
    Clean both semantic model and report (if both paths exist)

.EXAMPLE
    # Clean semantic model only
    .\cleanup_after_edit.ps1 -SemanticModelPath "IAM_FIELD_MAPPING.SemanticModel\definition"

.EXAMPLE
    # Clean report definition JSON files
    .\cleanup_after_edit.ps1 -ReportPath "IAM Portfolio Surverillance.Report\definition"

.EXAMPLE
    # Clean both
    .\cleanup_after_edit.ps1 -CleanBoth
#>

param(
    [Parameter(Mandatory=$false)]
    [string]$SemanticModelPath,
    
    [Parameter(Mandatory=$false)]
    [string]$ReportPath,
    
    [Parameter(Mandatory=$false)]
    [switch]$CleanBoth
)

$RemoveBomScript = Join-Path $PSScriptRoot "remove_all_boms.ps1"

if (-not (Test-Path $RemoveBomScript)) {
    Write-Host "Error: remove_all_boms.ps1 not found at $RemoveBomScript" -ForegroundColor Red
    exit 1
}

$totalFixed = 0

# Clean semantic model (TMDL files)
if ($CleanBoth -or $SemanticModelPath) {
    $modelPath = $SemanticModelPath
    if ($CleanBoth -and -not $modelPath) {
        $modelPath = "IAM_FIELD_MAPPING.SemanticModel\definition"
    }
    
    if ($modelPath -and (Test-Path $modelPath)) {
        Write-Host "`n📦 Cleaning semantic model TMDL files: $modelPath" -ForegroundColor Cyan
        & $RemoveBomScript -RootPath $modelPath -Extension "*.tmdl"
        $totalFixed++
    }
}

# Clean report definition (JSON files)
if ($CleanBoth -or $ReportPath) {
    $repPath = $ReportPath
    if ($CleanBoth -and -not $repPath) {
        $repPath = "IAM Portfolio Surverillance.Report\definition"
    }
    
    if ($repPath -and (Test-Path $repPath)) {
        Write-Host "`n📄 Cleaning report definition JSON files: $repPath" -ForegroundColor Cyan
        & $RemoveBomScript -RootPath $repPath -Extension "*.json"
        $totalFixed++
    }
}

if ($totalFixed -gt 0) {
    Write-Host "`n✅ BOM cleanup complete!`n" -ForegroundColor Green
}

if ($totalFixed -eq 0 -and -not ($SemanticModelPath -or $ReportPath -or $CleanBoth)) {
    Write-Host @"
Usage: .\cleanup_after_edit.ps1 [OPTIONS]

Options:
  -SemanticModelPath <path>   Path to semantic model definition folder
  -ReportPath <path>          Path to report definition folder
  -CleanBoth                  Clean both semantic model and report (auto-detect)

Examples:
  .\cleanup_after_edit.ps1 -SemanticModelPath "IAM_FIELD_MAPPING.SemanticModel\definition"
  .\cleanup_after_edit.ps1 -ReportPath "IAM Portfolio Surverillance.Report\definition"
  .\cleanup_after_edit.ps1 -CleanBoth
"@
}
