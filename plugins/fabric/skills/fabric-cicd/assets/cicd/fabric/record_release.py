"""Write a non-secret release audit record for a deployed artifact."""
import argparse
import datetime
import json
import os
import zipfile
from pathlib import Path

from release_contract import workspace_contract


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    with zipfile.ZipFile(args.artifact) as archive:
        data = json.loads(archive.read("managed-manifest.json"))
    try:
        workspace = workspace_contract(data, args.target)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    profile = (data.get("profiles") or {}).get(args.target, {})
    manual_boundary = bool((profile.get("verification") or {}).get("manual_boundary"))
    record = {
        "artifact": Path(args.artifact).name,
        "revision": data.get("revision"),
        "manifest": data.get("managed_items", []),
        "target": args.target,
        "target_workspace": workspace,
        "approver": os.environ.get("BUILD_REQUESTEDFOR", "Azure DevOps pull request reviewer"),
        "deployment_result": os.environ.get("AGENT_JOBSTATUS", "Succeeded"),
        "verification": "pending" if manual_boundary else "not-required",
        "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    out = Path(os.environ.get("BUILD_ARTIFACTSTAGINGDIRECTORY", "artifacts")) / "release-record.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Release record written to {out}")


if __name__ == "__main__":
    main()
