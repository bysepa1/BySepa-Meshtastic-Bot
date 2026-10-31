import tempfile
import unittest
import re
from pathlib import Path
import database
from commands.common import normalize_command, is_allowed_channel_command
from commands import COMMANDS
from commands.morse import handle as morse
from commands.maidenhead import handle as maidenhead

class SecurityTests(unittest.TestCase):
    def test_parser_requires_slash_and_valid_name(self):
        self.assertEqual(normalize_command("weather Valencia"), (None, []))
        self.assertEqual(normalize_command("/ping"), ("/ping", []))
        self.assertEqual(normalize_command("/ping; id"), (None, []))
        self.assertEqual(normalize_command("/ping\nid"), (None, []))
        self.assertEqual(normalize_command("/ping " + "A" * 201), (None, []))
        self.assertEqual(normalize_command("/ping 'unterminated"), (None, []))
        self.assertEqual(normalize_command("/exec id"), ("/exec", ["id"]))
        self.assertNotIn("/exec", COMMANDS)

    def test_commands_treat_shell_syntax_as_text(self):
        encoded = morse(["$(id)"], {})
        self.assertTrue(all(char in ".-/ " for char in encoded))
        self.assertIn("no válido", maidenhead(["JN01;id"], {}))

    def test_no_shell_or_dynamic_code_execution_calls(self):
        root = Path(__file__).resolve().parents[1]
        forbidden = re.compile(r"\b(?:os\.system|subprocess\.|eval\s*\(|exec\s*\()")
        for source in root.rglob("*.py"):
            if "tests" in source.parts or "__pycache__" in source.parts:
                continue
            self.assertIsNone(forbidden.search(source.read_text(encoding="utf-8")), str(source))

    def test_channel_policy(self):
        self.assertTrue(is_allowed_channel_command("Test", "/ping", []))
        self.assertFalse(is_allowed_channel_command("Test", "/ping", ["extra"]))
        self.assertFalse(is_allowed_channel_command("Test", "/morse", ["SOS"]))
        self.assertTrue(is_allowed_channel_command("Bots", "/morse", ["SOS"], COMMANDS))
        self.assertFalse(is_allowed_channel_command("Bots", "/exec", ["id"], COMMANDS))
        self.assertFalse(is_allowed_channel_command("Other", "/ping", []))

    def test_database_persistence_and_parameterization(self):
        with tempfile.TemporaryDirectory() as tmp:
            database.set_database_path(Path(tmp) / "test.sqlite3")
            database.initialize()
            database.record_message("!123", "Node'); DROP TABLE node_activity;--", "Bots")
            database.record_command("/ping")
            self.assertEqual(database.get_node("!123")["message_count"], 1)
            self.assertEqual(database.get_stats()["commands"], 1)
            database.record_message("!123", "Node", "Test", snr=7.5, rssi=-70)
            self.assertEqual(database.get_node("!123")["message_count"], 2)
            self.assertEqual(database.get_traffic()[0], 2)
            recent = database.get_recent_nodes()
            self.assertEqual(recent[0]["last_snr"], 7.5)
            self.assertEqual(recent[0]["last_rssi"], -70)

if __name__ == "__main__":
    unittest.main()
