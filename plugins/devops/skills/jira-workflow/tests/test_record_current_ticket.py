import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "record_current_ticket.py"
spec = importlib.util.spec_from_file_location("record_current_ticket", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TicketRecordTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.path = self.repo / "RESUME.md"

    def test_create_and_switch_ticket_preserves_other_content(self):
        self.path.write_bytes(b"Before\r\nOther area: preserved\r\n")
        module.record(self.repo, "FIN-101")
        first = self.path.read_bytes()
        self.assertIn(b"Before\r\nOther area: preserved\r\n", first)
        module.record(self.repo, "PBI-202")
        result = self.path.read_bytes()
        self.assertIn(b"Before\r\nOther area: preserved\r\n", result)
        self.assertIn(b"Current Jira ticket: PBI-202", result)
        self.assertNotIn(b"FIN-101", result)
        self.assertNotIn(b"\n", result.replace(b"\r\n", b""))
        module.record(self.repo, "PBI-202")
        self.assertEqual(result, self.path.read_bytes())

    def test_missing_or_invalid_key_does_not_create_file(self):
        for ticket in ("", "fin-123", "FIN-123 extra"):
            with self.assertRaises(ValueError):
                module.record(self.repo, ticket)
            self.assertFalse(self.path.exists())

    def test_ambiguous_and_reversed_markers_fail_without_changes(self):
        for content in (module.START, module.END + "\n" + module.START,
                        module.START + module.END + module.START + module.END):
            self.path.write_text(content, encoding="utf-8")
            before = self.path.read_bytes()
            with self.assertRaises(ValueError):
                module.record(self.repo, "FIN-123")
            self.assertEqual(before, self.path.read_bytes())

    def test_missing_file_is_created(self):
        module.record(self.repo, "FIN-123")
        self.assertIn("Current Jira ticket: FIN-123", self.path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
