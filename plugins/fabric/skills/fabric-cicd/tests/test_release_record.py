"""Release audit evidence must preserve manual verification boundaries."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "assets" / "cicd" / "fabric"))
spec = importlib.util.spec_from_file_location("record_release", SKILL / "assets" / "cicd" / "fabric" / "record_release.py")
record_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(record_release)


class ReleaseRecordTests(unittest.TestCase):
    def test_manual_boundary_is_pending_after_successful_deployment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "release.zip"
            manifest = {"revision": "abc", "managed_items": [], "profiles": {"UAT": {"workspace": {"id": "w", "name": "UAT"}, "verification": {"manual_boundary": True}}}}
            with zipfile.ZipFile(artifact, "w") as archive:
                archive.writestr("managed-manifest.json", json.dumps(manifest))
            before = dict(os.environ)
            try:
                os.environ["BUILD_ARTIFACTSTAGINGDIRECTORY"] = str(root / "out")
                os.environ["AGENT_JOBSTATUS"] = "Succeeded"
                old_argv = sys.argv
                sys.argv = ["record_release.py", "--artifact", str(artifact), "--target", "UAT"]
                record_release.main()
                data = json.loads((root / "out" / "release-record.json").read_text(encoding="utf-8"))
                self.assertEqual("Succeeded", data["deployment_result"])
                self.assertEqual("pending", data["verification"])
            finally:
                sys.argv = old_argv
                os.environ.clear(); os.environ.update(before)


if __name__ == "__main__":
    unittest.main()
