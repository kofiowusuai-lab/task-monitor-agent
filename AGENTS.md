# AGENTS.md

## Purpose

This repo provides a local Telegram task monitor for long-running agent work.

## Start

```bash
chmod +x bin/task-monitor
mkdir -p ~/.local/bin
ln -sf "$PWD/bin/task-monitor" ~/.local/bin/task-monitor
```

Create local credentials from `.env.example` in `~/.openclaw/.env`.

## Agent Rules

- Start a monitor before multi-step work.
- One user task gets one monitor.
- Keep the same monitor through retries and repairs.
- Mark stages `done` only after external verification.
- Do not commit `.env*`, `~/.openclaw/task-monitors`, logs, locks, or Telegram credentials.
- If Telegram fails, do not fabricate success; continue work and report the visibility failure.
