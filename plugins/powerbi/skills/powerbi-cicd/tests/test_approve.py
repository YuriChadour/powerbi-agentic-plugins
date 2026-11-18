from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import yaml

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parent / "scripts"))
sys.path.insert(0, str(TESTS))
import approve
from test_setup_contract import valid_setup
from setup_contract import dump_setup


class ApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.setup = self.root / "setup.yml"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write(self, value: dict) -> None:
        self.setup.write_text(dump_setup(value), encoding="utf-8")

    def test_blocking_gap_does_not_create_or_change_marker(self) -> None:
        value = valid_setup()
        value["gaps"] = [{"path": "binding", "reason": "unresolved"}]
        self.write(value)
        marker = self.root / "setup.approved"
        marker.write_text("unchanged", encoding="utf-8")
        self.assertEqual(1, approve.main(["--setup", str(self.setup)]))
        self.assertEqual("unchanged", marker.read_text(encoding="utf-8"))

    def test_valid_approval_records_exact_versioned_hash(self) -> None:
        self.write(valid_setup())
        self.assertEqual(0, approve.main(["--setup", str(self.setup)]))
        record = approve.verify_approval(self.setup)
        self.assertEqual(1, record["version"])
        self.assertEqual(approve.digest(self.setup), record["sha256"])

    def test_one_byte_change_invalidates_before_external_call(self) -> None:
        self.write(valid_setup())
        approve.main(["--setup", str(self.setup)])
        self.setup.write_bytes(self.setup.read_bytes() + b"\n")
        external = Mock()
        with self.assertRaisesRegex(ValueError, "changed after approval"):
            approve.verify_approval(self.setup)
            external()
        external.assert_not_called()


if __name__ == "__main__":
    unittest.main()
