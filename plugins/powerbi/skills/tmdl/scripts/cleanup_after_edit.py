#!/usr/bin/env python3
"""
Convenience wrapper to clean up TMDL/JSON files after editing by removing UTF-8 BOM.

Usage:
    python cleanup_after_edit.py --semantic-model PATH
    python cleanup_after_edit.py --report PATH
    python cleanup_after_edit.py --both
"""
import sys
import argparse
import subprocess
from pathlib import Path

def run_bom_removal(target_path, extension, verbose=False):
    """Run the remove_bom.py script on a target directory."""
    script_dir = Path(__file__).parent
    remove_bom_script = script_dir / "remove_bom.py"
    
    if not remove_bom_script.exists():
        print(f"Error: remove_bom.py not found at {remove_bom_script}", file=sys.stderr)
        return False
    
    cmd = [
        sys.executable,
        str(remove_bom_script),
        str(target_path),
        "--extension",
        extension
    ]
    
    if verbose:
        cmd.append("--verbose")
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running BOM removal: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Clean up TMDL/JSON files after editing by removing UTF-8 BOM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_after_edit.py --semantic-model "IAM_FIELD_MAPPING.SemanticModel/definition"
  python cleanup_after_edit.py --report "IAM Portfolio Surverillance.Report/definition"
  python cleanup_after_edit.py --both
  python cleanup_after_edit.py --both --verbose
        """
    )
    
    parser.add_argument(
        "--semantic-model",
        metavar="PATH",
        help="Path to semantic model definition folder (remove .tmdl BOM)"
    )
    parser.add_argument(
        "--report",
        metavar="PATH",
        help="Path to report definition folder (remove .json BOM)"
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="Clean both semantic model and report (auto-detect standard paths)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print details for every file checked"
    )
    
    args = parser.parse_args()
    
    if not (args.semantic_model or args.report or args.both):
        parser.print_help()
        return 0
    
    success = True
    
    # Clean semantic model (TMDL files)
    if args.both or args.semantic_model:
        model_path = args.semantic_model
        if args.both and not model_path:
            model_path = Path("IAM_FIELD_MAPPING.SemanticModel") / "definition"
        
        if model_path:
            model_path = Path(model_path)
            if model_path.exists():
                print(f"\n📦 Cleaning semantic model: {model_path}")
                success = run_bom_removal(model_path, "*.tmdl", args.verbose) and success
            else:
                print(f"⚠️  Semantic model path not found: {model_path}")
    
    # Clean report definition (JSON files)
    if args.both or args.report:
        report_path = args.report
        if args.both and not report_path:
            report_path = Path("IAM Portfolio Surverillance.Report") / "definition"
        
        if report_path:
            report_path = Path(report_path)
            if report_path.exists():
                print(f"\n📄 Cleaning report definition: {report_path}")
                success = run_bom_removal(report_path, "*.json", args.verbose) and success
            else:
                print(f"⚠️  Report path not found: {report_path}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
