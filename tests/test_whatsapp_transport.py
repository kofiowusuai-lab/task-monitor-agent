import importlib.machinery
import importlib.util
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "task-monitor"
loader = importlib.machinery.SourceFileLoader("task_monitor", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
tm = importlib.util.module_from_spec(spec)
loader.exec_module(tm)


class BridgeHandler(BaseHTTPRequestHandler):
    calls = []
    next_id = 1

    def log_message(self, *_args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        type(self).calls.append((self.path, payload))
        if self.path == "/send":
            response = {"success": True, "messageId": f"wa-{type(self).next_id}"}
            type(self).next_id += 1
            status = 200
        elif self.path == "/edit":
            response = {"success": True}
            status = 200
        else:
            response = {"error": "not found"}
            status = 404
        body = json.dumps(response).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class WhatsAppTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BridgeHandler.calls = []
        BridgeHandler.next_id = 1
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), BridgeHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.bridge_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        BridgeHandler.calls.clear()
        BridgeHandler.next_id = 1
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        tm.STATE_DIR = Path(self.temp.name) / "state"
        tm.ENV_FILE = Path(self.temp.name) / "missing-openclaw-env"
        tm.HERMES_ENV_FILE = Path(self.temp.name) / "missing-hermes-env"
        self.env = patch.dict(
            os.environ,
            {
                "HERMES_TASK_MONITOR": "1",
                "HERMES_TASK_MONITOR_FORCE_ENABLE": "1",
                "HERMES_WHATSAPP_CHAT_ID": "12345@lid",
                "HERMES_WHATSAPP_BRIDGE_URL": self.bridge_url,
            },
            clear=False,
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def config(self):
        return tm.load_env(transport="whatsapp")

    def state(self):
        now = time.time()
        return {
            "id": "tm_test0001",
            "chat_id": "12345@lid",
            "bot_id": f"whatsapp:{self.bridge_url}",
            "transport": "whatsapp",
            "lane": "default",
            "task_key": "test",
            "title": "WhatsApp lifecycle",
            "started_at": now,
            "message_started_at": now,
            "message_history": [],
            "rollover_count": 0,
            "stages": [{"name": "Build", "status": "active", "details": []}],
            "lanes": [],
            "notes": [],
            "closed": False,
            "result": None,
            "summary": None,
            "message_id": "wa-original",
            "last_edit_ts": 0,
            "last_progress_ts": now,
            "ticker_pid": None,
        }

    def test_load_env_resolves_whatsapp(self):
        config = self.config()
        self.assertEqual(config["transport"], "whatsapp")
        self.assertEqual(config["chat"], "12345@lid")
        self.assertEqual(config["bridge_url"], self.bridge_url)

    def test_send_and_edit_bridge_contract(self):
        config = self.config()
        sent = tm.send_message(config, "hello")
        self.assertTrue(sent["ok"])
        self.assertEqual(sent["messageId"], "wa-1")
        state = self.state()
        edited = tm.edit_message(config, state, "updated")
        self.assertTrue(edited["ok"])
        self.assertEqual(
            BridgeHandler.calls,
            [
                ("/send", {"chatId": "12345@lid", "message": "hello"}),
                ("/edit", {"chatId": "12345@lid", "messageId": "wa-original", "message": "updated"}),
            ],
        )

    def test_rollover_finalizes_old_card_and_continues(self):
        config = self.config()
        state = self.state()
        state["message_started_at"] = time.time() - tm.WHATSAPP_ROLLOVER_SECONDS - 1
        response = tm.maybe_rollover(config, state, "live status")
        self.assertTrue(response["ok"])
        self.assertTrue(response["rolled_over"])
        self.assertEqual(state["message_id"], "wa-1")
        self.assertEqual(state["rollover_count"], 1)
        self.assertEqual(state["message_history"][0]["message_id"], "wa-original")
        self.assertEqual(BridgeHandler.calls[0][0], "/edit")
        self.assertIn("Continuing in a fresh live card", BridgeHandler.calls[0][1]["message"])
        self.assertEqual(BridgeHandler.calls[1][0], "/send")
        self.assertIn("Continuation 1", BridgeHandler.calls[1][1]["message"])

    def test_finished_task_rolls_over_and_persists_final_card(self):
        config = self.config()
        state = self.state()
        state["closed"] = True
        state["result"] = "success"
        state["summary"] = "released"
        state["stages"][0]["status"] = "done"
        state["message_started_at"] = time.time() - tm.WHATSAPP_ROLLOVER_SECONDS - 1
        tm.push_update(state, config)
        saved = json.loads((tm.STATE_DIR / "tm_test0001.json").read_text())
        self.assertEqual(saved["message_id"], "wa-1")
        self.assertEqual(saved["result"], "success")
        self.assertTrue(saved["closed"])
        self.assertIn("released", BridgeHandler.calls[-1][1]["message"])


if __name__ == "__main__":
    unittest.main()
