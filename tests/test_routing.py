import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

# Keep the unit tests runnable without USB hardware or the Meshtastic package.
meshtastic = types.ModuleType("meshtastic")
serial_interface = types.ModuleType("meshtastic.serial_interface")
serial_interface.SerialInterface = lambda *args, **kwargs: None
meshtastic.serial_interface = serial_interface
pubsub = types.ModuleType("pubsub")
pubsub.pub = SimpleNamespace(subscribe=lambda *args, **kwargs: None)
sys.modules.setdefault("meshtastic", meshtastic)
sys.modules.setdefault("meshtastic.serial_interface", serial_interface)
sys.modules.setdefault("pubsub", pubsub)

import bysepa_bot_msh as bot
import database

class FakeInterface:
    def __init__(self):
        self.sent = []
        self.nodesByNum = {123: SimpleNamespace(user=SimpleNamespace(longName="NodoPrueba"))}
        self.nodes = {}
    def getLongName(self):
        return "EA5ABC JN01AB"
    def sendText(self, text, channelIndex=0):
        self.sent.append((text, channelIndex))

class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        database.set_database_path(Path(self.tmp.name) / "test.sqlite3")
        database.initialize()
        bot.database_available = True
        bot.channel_indexes = {"Bots": 1, "Test": 2}
        bot.processed_packets.clear()
        bot.last_command_time.clear()
        bot.last_node_response_time.clear()
        bot.outbound_response_times.clear()
        self.iface = FakeInterface()

    def tearDown(self):
        self.tmp.cleanup()

    def packet(self, text, channel, packet_id):
        return {"id": packet_id, "from": 123, "fromId": "!0000007b", "channel": channel,
                "decoded": {"text": text}, "hopStart": 3, "hopLimit": 2,
                "rxRssi": -70, "rxSnr": 7.5}

    def test_bot_channel_reply_uses_same_channel_and_names_sender(self):
        bot.on_message(self.packet("/morse SOS", 1, 1001), self.iface)
        self.assertEqual(len(self.iface.sent), 1)
        text, channel = self.iface.sent[0]
        self.assertEqual(channel, 1)
        self.assertEqual(text, "... --- ...")
        self.assertNotIn("[BySepaBot →", text)


    def test_invalid_weather_arguments_do_not_consume_cooldown(self):
        from unittest.mock import patch
        bot.on_message(self.packet("/weather", 1, 3001), self.iface)
        self.assertEqual(self.iface.sent, [])
        self.assertEqual(bot.last_command_time, {})
        with patch.dict(bot.COMMANDS, {"/weather": lambda args, ctx: "Clima simulado"}):
            bot.on_message(self.packet("/weather Valencia", 1, 3002), self.iface)
        # El comando válido sí pasa la validación y se registra antes de la consulta.
        self.assertIn((123, 1, "/weather"), bot.last_command_time)
        self.assertEqual(self.iface.sent[0][0], "Clima simulado")

    def test_mesh_is_request_only_and_status_is_not_exposed(self):
        self.assertIn("/mesh", __import__("commands").COMMANDS)
        self.assertNotIn("/status", __import__("commands").COMMANDS)
        bot.on_message(self.packet("texto normal", 1, 4001), self.iface)
        self.assertEqual(self.iface.sent, [])
        bot.on_message(self.packet("/mesh", 1, 4002), self.iface)
        self.assertEqual(len(self.iface.sent), 1)
        self.assertIn("actividad observada", self.iface.sent[0][0])


    def test_global_radio_response_limit(self):
        for i in range(bot.GLOBAL_RESPONSE_LIMIT + 1):
            packet = self.packet("/ping", 1, 5000 + i)
            packet["from"] = 1000 + i
            packet["fromId"] = f"!{1000 + i:08x}"
            bot.on_message(packet, self.iface)
        self.assertEqual(len(self.iface.sent), bot.GLOBAL_RESPONSE_LIMIT)

    def test_test_channel_only_allows_ping_without_args(self):
        bot.on_message(self.packet("/morse SOS", 2, 2001), self.iface)
        self.assertEqual(self.iface.sent, [])
        bot.on_message(self.packet("/ping extra", 2, 2002), self.iface)
        self.assertEqual(self.iface.sent, [])
        bot.on_message(self.packet("/ping", 2, 2003), self.iface)
        self.assertEqual(len(self.iface.sent), 1)
        self.assertEqual(self.iface.sent[0][1], 2)
        self.assertTrue(self.iface.sent[0][0].startswith("/pong\n"))

if __name__ == "__main__":
    unittest.main()
