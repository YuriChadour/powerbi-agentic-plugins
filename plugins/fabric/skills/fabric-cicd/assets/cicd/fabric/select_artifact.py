"""Choose the verified artifact PROD must consume for the merge that triggered it.

A completed pull request into the PROD branch resolves to its source branch and
source commit. The TEST branch maps to the TEST pipeline's build, ``hotfix/*``
to the HOTFIX pipeline's build; any other source, or a missing successful build
for that commit, blocks before any target write.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml
from profile_loader import load_manifest


def choose(source_branch: str, test_branch: str, test_pipeline: str, hotfix_pipeline: str) -> tuple[str, str, str]:
    """Return (artifact target, pipeline name, source branch) or raise SystemExit."""
    if source_branch == test_branch:
        return "TEST", test_pipeline, source_branch
    if source_branch.startswith("hotfix/"):
        return "HOTFIX", hotfix_pipeline, source_branch
    raise SystemExit(f"merge into PROD came from '{source_branch}'; only '{test_branch}' or 'hotfix/*' pull requests may be promoted")


def choose_profile(source_branch: str, profiles: dict, target: str) -> tuple[str, str, str]:
    """Resolve one accepted source profile from the approved manifest, fail closed."""
    destination = profiles.get(target)
    if not isinstance(destination, dict):
        raise SystemExit(f"target profile '{target}' is not configured")
    accepted = (destination.get("promotion") or {}).get("accepts_from", [])
    matches = []
    for key in accepted:
        profile = profiles.get(key, {})
        branch = profile.get("source_branch")
        if isinstance(branch, str) and fnmatch.fnmatchcase(source_branch, branch):
            pipeline = (profile.get("azure_devops") or {}).get("pipeline_name")
            if not isinstance(pipeline, str) or not pipeline:
                raise SystemExit(f"source profile '{key}' has no pipeline name")
            matches.append((key, pipeline, source_branch))
    if len(matches) != 1:
        raise SystemExit(f"source branch '{source_branch}' is not routed to exactly one accepted profile for {target}")
    return matches[0]


def api(url: str, token: str) -> dict:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


def merged_pull_request(org_url: str, project: str, repo: str, prod_branch: str, merge_commit: str, token: str) -> dict:
    base = f"{org_url.rstrip('/')}/{urllib.parse.quote(project)}/_apis/git/repositories/{urllib.parse.quote(repo)}"
    query = urllib.parse.urlencode({"searchCriteria.status": "completed", "searchCriteria.targetRefName": f"refs/heads/{prod_branch}", "$top": 50, "api-version": "7.1"})
    for pr in api(f"{base}/pullrequests?{query}", token).get("value", []):
        if pr.get("lastMergeCommit", {}).get("commitId") == merge_commit:
            return pr
    raise SystemExit(f"no completed pull request produced PROD revision {merge_commit}; direct pushes are not promoted")


def successful_build(org_url: str, project: str, pipeline: str, branch: str, commit: str, token: str) -> int:
    base = f"{org_url.rstrip('/')}/{urllib.parse.quote(project)}/_apis/build/builds"
    query = urllib.parse.urlencode({"branchName": f"refs/heads/{branch}", "resultFilter": "succeeded", "statusFilter": "completed", "$top": 50, "api-version": "7.1"})
    for build in api(f"{base}?{query}", token).get("value", []):
        if build.get("definition", {}).get("name") == pipeline and build.get("sourceVersion") == commit:
            return int(build["id"])
    raise SystemExit(f"no successful '{pipeline}' build exists for {branch} at {commit}; run and verify it before promoting")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--org-url", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--prod-branch", required=True)
    parser.add_argument("--test-branch", required=True)
    parser.add_argument("--test-pipeline", required=True)
    parser.add_argument("--hotfix-pipeline", required=True)
    parser.add_argument("--merge-commit", required=True)
    parser.add_argument("--download-to", required=True, type=Path)
    parser.add_argument("--profiles", type=Path, help="approved managed-items.yml containing profiles")
    parser.add_argument("--target-profile", help="promotion destination profile")
    args = parser.parse_args()
    token = os.environ.get("SYSTEM_ACCESSTOKEN")
    if not token:
        raise SystemExit("SYSTEM_ACCESSTOKEN is not available")

    pr = merged_pull_request(args.org_url, args.project, args.repository, args.prod_branch, args.merge_commit, token)
    source_branch = pr["sourceRefName"].removeprefix("refs/heads/")
    source_commit = pr["lastMergeSourceCommit"]["commitId"]
    if bool(args.profiles) != bool(args.target_profile):
        raise SystemExit("--profiles and --target-profile must be supplied together")
    if args.profiles:
        profiles = load_manifest(args.profiles).get("profiles")
        if not isinstance(profiles, dict):
            raise SystemExit("approved manifest has no profiles registry")
        target, pipeline, branch = choose_profile(source_branch, profiles, args.target_profile)
    else:
        target, pipeline, branch = choose(source_branch, args.test_branch, args.test_pipeline, args.hotfix_pipeline)
    build_id = successful_build(args.org_url, args.project, pipeline, branch, source_commit, token)
    artifact = f"fabric-{target.lower()}-release"
    args.download_to.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["az", "pipelines", "runs", "artifact", "download", "--run-id", str(build_id), "--artifact-name", artifact, "--path", str(args.download_to),
         "--org", args.org_url, "--project", args.project],
        check=True, env={**os.environ, "AZURE_DEVOPS_EXT_PAT": token},
    )
    print(f"Selected {target} artifact '{artifact}' from build {build_id} (source {branch} @ {source_commit})")
    print(f"##vso[task.setvariable variable=artifactTarget]{target}")
    print(f"##vso[task.setvariable variable=artifactDir]{args.download_to / artifact}")
    print(f"##vso[task.setvariable variable=artifactZip]{args.download_to / artifact / (artifact + '.zip')}")
    print(f"##vso[task.setvariable variable=artifactRevision]{source_commit}")


if __name__ == "__main__":
    sys.exit(main())
