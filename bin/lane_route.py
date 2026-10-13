#!/usr/bin/env python3
"""Lane routing resolver for task-monitor.

Restored 2026-09-12 (K order: profile lanes always). The shared task-monitor
script imports `lane_route` from its own directory and calls
``resolve(lane, env)`` for every Telegram monitor. This module maps a lane name
to its own bot token + chat id, loaded from ~/.openclaw/telegram_routes.json.

routes file shape:
{
  "kedolabs": {"token": "8955123038:AA...", "chat": "5426093479"},
  "ugc":      {...}, "before_freedom": {...}
}

Resolution order inside resolve():
1. routes file entry for the lane  (dedicated lane -> its own route)
2. env vars (HERMES_TASK_MONITOR_OVERRIDE_TOKEN/_CHAT, or default token + chat)
Returns {"token": str, "chat": str} — both may be None so the caller applies
its hardened pin fallback for the default lane.
"""
import json
import os
from pathlib import Path

ROUTES_FILE = Path.home() / ".openclaw" / "telegram_routes.json"


def _load_routes():
    try:
        data = json.loads(ROUTES_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def resolve(lane, env):
    """Return {"token": ..., "chat": ...} for `lane`.

    `env` is the merged process+file environment the caller built. Both keys may
    be None when nothing is configured; task-monitor then applies the pinned
    default route (K's hardened pin for the default lane).
    """
    env = env or {}
    routes = _load_routes()
    entry = routes.get(lane) or {}
    token = entry.get("token") or env.get("HERMES_TASK_MONITOR_OVERRIDE_TOKEN")
    chat = entry.get("chat") or env.get("HERMES_TASK_MONITOR_OVERRIDE_CHAT")
    if not token:
        token = env.get("HERMES_TELEGRAM_BOT_TOKEN") or env.get("TELEGRAM_BOT_TOKEN")
    if not chat:
        chat = env.get("HERMES_TELEGRAM_CHAT_ID") or env.get("TELEGRAM_CHAT_ID")
    return {"token": token, "chat": chat}
