param(
    [Parameter(Mandatory=$true, HelpMessage="Root directory to scan for BOM files")]
    [string]$RootPath,
    
    [Parameter(Mandatory=$false, HelpMessage="File extension to filter (default: *.json)")]
    [string]$Extension = "*.json",
    
    [Parameter(Mandatory=$false, HelpMessage="Encoding to use (default: UTF8)")]
    [string]$Encoding = "UTF8"
)

# Validate path exists
if (-not (Test-Path -Path $RootPath)) {
    Write-Host "Error: Path does not exist: $RootPath" -ForegroundColor Red
    exit 1
}

$files = Get-ChildItem -Path $RootPath -Recurse -Include $Extension -ErrorAction SilentlyContinue

if ($files.Count -eq 0) {
    Write-Host "No files matching '$Extension' found in $RootPath"
    exit 0
}

$count = 0
foreach ($f in $files) {
    try {
        # Force re-save: read content and write back with UTF8 no BOM encoding
        # This reliably removes BOM even if detection fails
        $content = Get-Content -Raw -Path $f.FullName
        $utf8NoBOM = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($f.FullName, $content, $utf8NoBOM)
        
        $count++
        Write-Host "✓ Fixed: $($f.Name)" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error on $($f.Name): $_" -ForegroundColor Red
    }
}

Write-Host "`nTotal files re-encoded: $count / $($files.Count)" -ForegroundColor Cyan
