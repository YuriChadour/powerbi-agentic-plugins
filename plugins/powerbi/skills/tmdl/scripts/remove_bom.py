#!/usr/bin/env python3
"""
Remove UTF-8 BOM from files in a directory tree.

Usage:
    python remove_bom.py <root_path> [--extension .json] [--verbose]
"""
import os
import sys
import argparse
from pathlib import Path

def remove_bom(file_path, verbose=False):
    """Remove UTF-8 BOM from a file by force re-saving.
    
    Reads file content and re-writes using UTF-8 without BOM encoding.
    This reliably removes BOM even if initial detection fails.
    
    Args:
        file_path: Path to the file to process
        verbose: Print detailed output
    
    Returns:
        bool: True if file was processed, False on error
    """
    try:
        # Force re-save: read as binary, decode, write back as UTF-8 no BOM
        with open(file_path, 'rb') as f:
            content_bytes = f.read()
        
        # Decode content (handles BOM automatically)
        text = content_bytes.decode('utf-8-sig')  # utf-8-sig strips BOM if present
        
        # Write back using UTF-8 without BOM
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        if verbose:
            print(f"✓ [FIXED] {file_path}")
        return True
    except Exception as e:
        print(f"✗ [ERROR] {file_path}: {e}", file=sys.stderr)
    
    return False

def main():
    parser = argparse.ArgumentParser(
        description="Remove UTF-8 BOM from files in a directory tree"
    )
    parser.add_argument(
        'root_path',
        help='Root directory to scan for BOM files'
    )
    parser.add_argument(
        '--extension',
        default='*.json',
        help='File extension to filter (default: *.json)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print details for every file checked'
    )
    
    args = parser.parse_args()
    
    # Validate path exists
    root_path = Path(args.root_path)
    if not root_path.exists():
        print(f"Error: Path does not exist: {args.root_path}", file=sys.stderr)
        sys.exit(1)
    
    # Find all matching files
    json_files = list(root_path.rglob(args.extension))
    
    if not json_files:
        print(f"No files matching '{args.extension}' found in {args.root_path}")
        sys.exit(0)
    
    fixed_count = 0
    for json_file in json_files:
        if remove_bom(str(json_file), verbose=args.verbose):
            fixed_count += 1
    
    print(f"\n📊 Summary:")
    print(f"  Total files processed: {fixed_count}")
    print(f"  Total files scanned: {len(json_files)}")
    
    return 0 if fixed_count >= 0 else 1

if __name__ == '__main__':
    sys.exit(main())
