# TMDL Skill Scripts

Utility scripts for maintaining TMDL and report definition files.

## BOM Removal Scripts

UTF-8 Byte Order Mark (BOM) can cause encoding issues in Power BI and other tools. These scripts remove BOM from text files after editing.

### Generic Scripts

#### `remove_bom.py` (Python)
Cross-platform script to remove UTF-8 BOM from files.

**Usage:**
```bash
python remove_bom.py <root_path> [--extension .json] [--verbose]
```

**Parameters:**
- `root_path` (required): Root directory to scan
- `--extension` (optional, default: `*.json`): File extension pattern
- `--verbose` (optional): Print details for each file checked

**Examples:**
```bash
python remove_bom.py "path/to/definition"
python remove_bom.py "path/to/definition" --extension "*.tmdl"
python remove_bom.py "path/to/definition" --extension "*.tmdl" --verbose
```

#### `remove_all_boms.ps1` (PowerShell) — Recommended
Windows PowerShell script to remove UTF-8 BOM from files by force re-saving.

**Usage:**
```powershell
.\remove_all_boms.ps1 -RootPath <path> [-Extension <pattern>]
```

**Parameters:**
- `-RootPath` (required): Root directory to scan
- `-Extension` (optional, default: `*.json`): File extension pattern

**Examples:**
```powershell
.\remove_all_boms.ps1 -RootPath "IAM_FIELD_MAPPING.SemanticModel\definition" -Extension "*.tmdl"
.\remove_all_boms.ps1 -RootPath "IAM Portfolio Surverillance.Report\definition" -Extension "*.json"
.\remove_all_boms.ps1 -RootPath "path\to\definition"
```

**How it works:**
- Reads file content as a raw string
- Forces re-write using `System.Text.UTF8Encoding($false)` (UTF-8 without BOM)
- Processes all matching files in the directory tree recursively
- Reports each file as it's processed

### Convenience Wrappers

Use these for common workflows after making edits to semantic models or reports.

#### `cleanup_after_edit.ps1` (PowerShell)
Wrapper that cleans semantic model TMDL files and/or report JSON files in one command.

**Usage:**
```powershell
.\cleanup_after_edit.ps1 -SemanticModelPath <path>
.\cleanup_after_edit.ps1 -ReportPath <path>
.\cleanup_after_edit.ps1 -CleanBoth
```

**Parameters:**
- `-SemanticModelPath`: Path to semantic model definition folder (cleans `.tmdl` files)
- `-ReportPath`: Path to report definition folder (cleans `.json` files)
- `-CleanBoth`: Auto-detect and clean both standard locations

**Examples:**
```powershell
# Clean semantic model after editing
.\cleanup_after_edit.ps1 -SemanticModelPath "IAM_FIELD_MAPPING.SemanticModel\definition"

# Clean report after editing
.\cleanup_after_edit.ps1 -ReportPath "IAM Portfolio Surverillance.Report\definition"

# Clean both
.\cleanup_after_edit.ps1 -CleanBoth
```

#### `cleanup_after_edit.py` (Python)
Cross-platform wrapper for common cleanup workflows.

**Usage:**
```bash
python cleanup_after_edit.py --semantic-model <path>
python cleanup_after_edit.py --report <path>
python cleanup_after_edit.py --both [--verbose]
```

**Parameters:**
- `--semantic-model`: Path to semantic model definition folder (cleans `.tmdl` files)
- `--report`: Path to report definition folder (cleans `.json` files)
- `--both`: Auto-detect and clean both standard locations
- `--verbose` (optional): Print details for each file

**Examples:**
```bash
# Clean semantic model after editing
python cleanup_after_edit.py --semantic-model "IAM_FIELD_MAPPING.SemanticModel/definition"

# Clean report after editing
python cleanup_after_edit.py --report "IAM Portfolio Surverillance.Report/definition"

# Clean both with verbose output
python cleanup_after_edit.py --both --verbose
```

## Recommended Workflow

After editing TMDL or report JSON files:

1. **Make your changes** in the semantic model or report
2. **Verify changes** are correct
3. **Run cleanup** to remove BOM:
   ```powershell
   # Windows PowerShell
   .\cleanup_after_edit.ps1 -CleanBoth
   
   # Cross-platform (Python)
   python cleanup_after_edit.py --both
   ```
4. **Commit** the cleaned files

## Why BOM Removal?

UTF-8 Byte Order Mark (BOM) is a 3-byte sequence (`EF BB BF`) at the start of files. While technically valid UTF-8, it causes critical issues:

- **Power BI import fails** with error: `Cannot read 'definition/tables/...'. Only text with UTF8 encoding without BOM (byte order marks) is supported. Detected BOM: 'UTF-8'`
- **Fabric semantic model deployment fails** for the same reason
- **TMDL parsers reject** files with BOM
- **JSON parsing may fail** in strict validators
- **Version control systems** may flag files as binary instead of text

**Solution:** Always run BOM removal after editing TMDL or JSON files to ensure clean UTF-8 encoding without BOM. The cleanup scripts use a force re-save approach that reliably removes BOM even if detection fails.
