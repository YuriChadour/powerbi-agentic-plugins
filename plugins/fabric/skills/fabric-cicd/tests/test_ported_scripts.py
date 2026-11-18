"""Offline checks for the ported deployment scripts (no Fabric access)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
CICD = SKILL / "assets" / "cicd"
FABRIC = CICD / "fabric"
WS = {env: f"{i}{i}{i}{i}{i}{i}{i}{i}-1111-4111-8111-111111111111" for i, env in enumerate(("DEV", "TEST", "PROD", "HOTFIX"), 1)}
FORBIDDEN = re.compile(r"BAM_|SH_SD|Servicing Oversight|Analytics Reporting|powerbi eot|UAT", re.IGNORECASE)


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True)


def synthetic_repo(root: Path) -> None:
    for name, content in {
        "Lake.Lakehouse/.platform": "{}",
        "Nb.Notebook/notebook-content.py": "print(1)\n",
        "Nb.Notebook/.platform": "{}",
        "Copy.CopyJob/copyjob-content.json": "{}",
        "Copy.CopyJob/.platform": "{}",
        "Pipe.DataPipeline/pipeline-content.json": "{}",
        "Pipe.DataPipeline/.platform": "{}",
    }.items():
        path = root / "fabric" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    cicd = root / "cicd" / "fabric"
    cicd.mkdir(parents=True)
    for source in FABRIC.glob("*.py"):
        (cicd / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (cicd / "parameter.yml").write_text("find_replace: []\n", encoding="utf-8")
    items = [
        {"folder": "Lake.Lakehouse", "type": "Lakehouse", "dependencies": []},
        {"folder": "Nb.Notebook", "type": "Notebook", "dependencies": ["Lake.Lakehouse"]},
        {"folder": "Copy.CopyJob", "type": "CopyJob", "dependencies": ["Lake.Lakehouse"]},
        {"folder": "Pipe.DataPipeline", "type": "DataPipeline", "dependencies": ["Copy.CopyJob"]},
    ]
    lines = ["version: 1", "source_root: fabric"]
    for env, guid in WS.items():
        lines += [f"{env.lower()}_workspace:", f"  id: {guid}", f"  name: WS {env}", "  capacity:", "    id: cap"]
    lines += ["deployment_identity:", "  app_id: app", "managed_items:"]
    for item in items:
        lines += [f"  - folder: {item['folder']}", f"    type: {item['type']}", f"    dependencies: {json.dumps(item['dependencies'])}"]
    (cicd / "managed-items.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")


class PortedScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        synthetic_repo(self.root)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"], cwd=self.root, check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build(self, target: str = "TEST") -> Path:
        validate = run("cicd/fabric/validate.py", "--output", "artifacts/managed-manifest.json", cwd=self.root)
        self.assertEqual(0, validate.returncode, validate.stderr)
        build = run("cicd/fabric/build_release.py", "--validation", "artifacts/managed-manifest.json", "--out", "artifacts/r.zip", "--target", target, cwd=self.root)
        self.assertEqual(0, build.returncode, build.stderr)
        return self.root / "artifacts" / "r.zip"

    def test_no_project_specific_names_remain(self) -> None:
        for path in CICD.rglob("*.py"):
            self.assertIsNone(FORBIDDEN.search(path.read_text(encoding="utf-8")), path.name)

    def test_secret_scan_passes_on_shipped_scripts(self) -> None:
        result = run(str(CICD / "shared" / "secret_scan.py"), "--root", str(SKILL / "assets"), cwd=SKILL)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_validate_accepts_copy_jobs_and_four_environments(self) -> None:
        manifest = json.loads(self.build().parent.joinpath("managed-manifest.json").read_text())
        self.assertEqual(["DEV", "TEST", "PROD", "HOTFIX"], manifest["environments"])
        self.assertIn("CopyJob", {item["type"] for item in manifest["managed_items"]})

    def test_unlisted_copy_job_fails_validation(self) -> None:
        extra = self.root / "fabric" / "Other.CopyJob"
        extra.mkdir()
        (extra / "copyjob-content.json").write_text("{}", encoding="utf-8")
        result = run("cicd/fabric/validate.py", "--output", "artifacts/m.json", cwd=self.root)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Other.CopyJob", result.stderr)

    def test_pipeline_invoking_unmanaged_copy_job_fails(self) -> None:
        guid = "abababab-1111-4111-8111-111111111111"
        (self.root / "fabric" / "Copy.CopyJob" / ".platform").write_text(json.dumps({"config": {"logicalId": guid}}), encoding="utf-8")
        pipeline = self.root / "fabric" / "Pipe.DataPipeline" / "pipeline-content.json"
        activity = {"properties": {"activities": [{"type": "InvokeCopyJob", "typeProperties": {"copyJobId": guid}}]}}
        pipeline.write_text(json.dumps(activity), encoding="utf-8")
        self.assertEqual(0, run("cicd/fabric/validate.py", "--output", "artifacts/m.json", cwd=self.root).returncode)
        activity["properties"]["activities"][0]["typeProperties"]["copyJobId"] = "cdcdcdcd-1111-4111-8111-111111111111"
        pipeline.write_text(json.dumps(activity), encoding="utf-8")
        result = run("cicd/fabric/validate.py", "--output", "artifacts/m.json", cwd=self.root)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("not a managed CopyJob", result.stderr)

    def test_verified_artifact_extracts_and_tamper_is_rejected(self) -> None:
        artifact = self.build()
        out = self.root / "extracted"
        ok = run("cicd/fabric/deploy_artifact.py", "--artifact", str(artifact), "--environment", "TEST", "--extract-to", str(out), cwd=self.root)
        self.assertEqual(0, ok.returncode, ok.stderr)
        self.assertTrue((out / "cicd" / "fabric" / "deploy_runner.py").exists())
        tampered = self.root / "tampered.zip"
        with zipfile.ZipFile(artifact) as src, zipfile.ZipFile(tampered, "w") as dst:
            for info in src.infolist():
                data = src.read(info)
                dst.writestr(info, data + b"#" if info.filename.endswith("deploy_runner.py") else data)
        bad = run("cicd/fabric/deploy_artifact.py", "--artifact", str(tampered), "--environment", "TEST", "--extract-to", str(self.root / "bad"), cwd=self.root)
        self.assertNotEqual(0, bad.returncode)
        self.assertIn("hash mismatch", bad.stderr + bad.stdout)

    def test_wrong_environment_is_rejected(self) -> None:
        artifact = self.build("TEST")
        result = run("cicd/fabric/deploy_artifact.py", "--artifact", str(artifact), "--environment", "PROD", "--verify-only", cwd=self.root)
        self.assertNotEqual(0, result.returncode)


if __name__ == "__main__":
    unittest.main()
