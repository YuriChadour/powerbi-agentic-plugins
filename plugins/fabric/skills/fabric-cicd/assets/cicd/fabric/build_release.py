"""Build an immutable release bundle from the checked-out revision."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

import yaml

from release_contract import artifact_digest, deployment_relevant_names
from profile_loader import profile, profile_keys


def revision(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


def file_hashes(staging: Path) -> dict[str, str]:
    return {
        str(path.relative_to(staging)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(staging.rglob("*"))
        if path.is_file()
    }


def materialize_contract_overlay(staging: Path, contract_path: Path, data: dict, target: str, expected_revision: str) -> None:
    """Make a reviewed target contract part of the immutable artifact."""
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    if not isinstance(contract, dict) or contract.get("target_class") != target:
        raise SystemExit(f"{target} artifact requires a matching target contract")
    workspace, capacity, source, lakehouse = (contract.get(key) or {} for key in ("workspace", "capacity", "source", "lakehouse"))
    if not isinstance(workspace.get("id"), str) or not isinstance(workspace.get("name"), str) or not isinstance(capacity, dict):
        raise SystemExit(f"{target} target contract is missing workspace or capacity")
    if source.get("revision") != expected_revision:
        raise SystemExit(f"{target} target contract revision does not match the selected revision")
    if not isinstance(lakehouse.get("id"), str) or lakehouse.get("schemas_enabled") is not True:
        raise SystemExit(f"{target} target contract must identify a schema-enabled Lakehouse")
    data[f"{target.lower()}_workspace"] = {"id": workspace["id"], "name": workspace["name"], "capacity": capacity}
    config_path = staging / "cicd" / "fabric" / "config.yml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    config.setdefault("core", {}).setdefault("workspace_id", {})[target] = workspace["id"]
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    parameter_path = staging / "cicd" / "fabric" / "parameter.yml"
    parameter = yaml.safe_load(parameter_path.read_text(encoding="utf-8")) or {}
    for rule in parameter.get("find_replace", []):
        values = rule.get("replace_value")
        if isinstance(values, dict) and target not in values:
            fallback = values.get("TEST") or values.get("DEV")
            if fallback is not None:
                values[target] = fallback
    parameter_path.write_text(yaml.safe_dump(parameter, sort_keys=False), encoding="utf-8")
    (staging / "target-contract.json").write_text(json.dumps(contract, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--validation", default="artifacts/managed-manifest.json")
    parser.add_argument("--out", default="artifacts/release.zip")
    parser.add_argument("--target", required=True)
    parser.add_argument("--target-contract")
    parser.add_argument("--expected-revision")
    args = parser.parse_args()

    root, out = Path(args.root).resolve(), Path(args.out).resolve()
    data = json.loads((root / args.validation).resolve().read_text(encoding="utf-8"))
    profile_manifest = yaml.safe_load((root / "cicd" / "fabric" / "managed-items.yml").read_text(encoding="utf-8")) or {}
    if isinstance(profile_manifest.get("profiles"), dict):
        data["profiles"] = profile_manifest["profiles"]
    target_contract = args.target_contract
    if args.target not in profile_keys(data):
        raise SystemExit(f"target '{args.target}' is not a configured profile")
    mode = profile(data, args.target).get("deployment_mode", "standard")
    if mode == "contract" and not target_contract:
        raise SystemExit(f"target '{args.target}' requires --target-contract")
    if target_contract and mode != "contract":
        raise SystemExit(f"target '{args.target}' is not configured for contract deployment")
    data["revision"] = revision(root)
    data["artifact_target"] = args.target
    if args.expected_revision and data["revision"] != args.expected_revision:
        raise SystemExit(f"checked-out revision {data['revision']} does not match expected revision {args.expected_revision}")

    staging = out.parent / "release-staging"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(root / "fabric", staging / "fabric", ignore=ignore)
    shutil.copytree(root / "cicd" / "fabric", staging / "cicd" / "fabric", ignore=ignore)
    if target_contract:
        materialize_contract_overlay(staging, Path(target_contract).resolve(), data, args.target, data["revision"])
    (staging / "managed-manifest.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    hashes = file_hashes(staging)
    source_hashes = {name: value for name, value in hashes.items() if name in deployment_relevant_names(set(hashes))}
    (staging / "release-metadata.json").write_text(
        json.dumps(
            {"artifact_target": args.target, "revision": data["revision"], "source_hashes": source_hashes, "managed_manifest": "managed-manifest.json"},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    (staging / "content-hashes.json").write_text(json.dumps(file_hashes(staging), indent=2) + "\n", encoding="utf-8")

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(staging))
    print(f"Release artifact: {out}")
    print(f"Revision: {data['revision']}")
    print(f"Artifact SHA-256: {artifact_digest(out)}")


if __name__ == "__main__":
    main()
