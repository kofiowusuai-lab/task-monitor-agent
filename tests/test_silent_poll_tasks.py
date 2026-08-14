import importlib.machinery
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "bin" / "task-monitor"
loader = importlib.machinery.SourceFileLoader("task_monitor_silent", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
tm = importlib.util.module_from_spec(spec)
loader.exec_module(tm)


class SilentPollTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        tm.STATE_DIR = Path(self.temp.name) / "state"

    def test_known_recorrido_poll_titles_are_silent(self):
        for title in (
            "Process Recorrido support inbox",
            "Process Recorrido support email",
            "Process Recorrido support queue",
            "Recorrido support inbox processing",
            "Recorrido support inbox sync",
        ):
            self.assertTrue(tm.is_silent_poll_task(tm.task_key_of(title)))
        self.assertFalse(tm.is_silent_poll_task("Reply to Recorrido customer"))

    def test_start_persists_monitor_without_sending_or_ticker(self):
        args = SimpleNamespace(
            title="Process Recorrido support inbox",
            stages="Sync,Review,Reply,Status",
            task=None,
            lane="ugc",
            transport="telegram",
            force=False,
        )
        config = {
            "transport": "telegram",
            "chat": "12345",
            "identity": "bot-test",
            "token": "unused",
        }
        output = io.StringIO()
        with (
            patch.object(tm, "load_env", return_value=config),
            patch.object(tm, "find_reusable_monitor", return_value=None),
            patch.object(tm, "send_message") as send,
            patch.object(tm, "spawn_ticker") as ticker,
            redirect_stdout(output),
        ):
            tm.cmd_start(args)

        monitor_id = output.getvalue().strip()
        state = json.loads((tm.STATE_DIR / f"{monitor_id}.json").read_text())
        self.assertTrue(state["silent"])
        self.assertIsNone(state["message_id"])
        send.assert_not_called()
        ticker.assert_not_called()

    def test_silent_progress_is_saved_without_transport_edit(self):
        state = {
            "id": "tm_silent1",
            "silent": True,
            "last_progress_ts": 0,
            "last_edit_ts": 0,
        }
        with patch.object(tm, "edit_message") as edit:
            tm.push_update(state, {"transport": "telegram", "token": "unused"})
        saved = json.loads((tm.STATE_DIR / "tm_silent1.json").read_text())
        self.assertGreater(saved["last_progress_ts"], 0)
        edit.assert_not_called()


if __name__ == "__main__":
    unittest.main()