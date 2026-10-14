# task-monitor-agent

Local Telegram and WhatsApp progress monitor for agent workflows. It creates one message per task and edits that message as stages move from pending to active to done or failed.

It is useful for long builds, renders, deploys, multi-agent workflows, research passes, and production runs where the user should not stare at a silent terminal.

## Requirements

Use Python 3 on macOS or Linux and a shell for the installation commands. The CLI uses Python standard-library modules, including Unix-only `fcntl` locks and process signals; native Windows support is not provided. No pip packages are required. A Telegram bot/chat or a running compatible WhatsApp bridge is required for visible delivery. The bridge itself is not included.

## Quick Start

```bash
git clone https://github.com/kofiowusuai-lab/task-monitor-agent.git
cd task-monitor-agent
chmod +x bin/task-monitor
mkdir -p ~/.local/bin
ln -sf "$PWD/bin/task-monitor" ~/.local/bin/task-monitor
```

Make sure `~/.local/bin` is on `PATH`.

Create your local Telegram env:

```bash
mkdir -p ~/.openclaw
cp .env.example ~/.openclaw/.env
```

Edit `~/.openclaw/.env` with the user's own Telegram bot token and chat ID.

For a local Hermes WhatsApp bridge, select WhatsApp per task:

```bash
ID=$(task-monitor start "Publish repos" --transport whatsapp --stages "Audit,Package,Test,Push,Verify")
```

Configure `HERMES_WHATSAPP_CHAT_ID` (or `WHATSAPP_HOME_CHANNEL`) and, when the bridge is not on port 3000, `HERMES_WHATSAPP_BRIDGE_URL`. Set `HERMES_TASK_MONITOR_TRANSPORT=whatsapp` to make WhatsApp the default. WhatsApp edits expire after roughly 15 minutes, so the monitor automatically finalizes the current card and continues in a fresh card before the edit window closes.

## Usage

```bash
ID=$(task-monitor start "Publish repos" --stages "Audit,Package,Test,Push,Verify")
task-monitor stage "$ID" Audit done
task-monitor stage "$ID" Package active --detail "Preparing README and AGENTS files"
task-monitor detail "$ID" "voiceswap packaged"
task-monitor note "$ID" "Holding any repo with real secrets"
task-monitor finish "$ID" --success --summary "All clean repos pushed"
```

Show the current rendered monitor text:

```bash
task-monitor show "$ID"
```

### Stage progression

Planned stages are sequential. When a later planned stage becomes `active` or `done`, earlier pending stages settle to `done`, preventing stale hourglasses during the job. Unplanned repair stages appear before the next pending planned stage without completing future work. A successful `finish` settles all remaining rows; a failed `finish` marks unfinished rows failed. Use `lane` rows for parallel workers.

## Environment

The monitor starts with nonempty process environment values, then overlays `~/.openclaw/.env` and `~/.hermes/.env` in that order. File values therefore override process values, and the Hermes file wins when both files define the same key. These are simple `KEY=value` files: do not add shell `export` prefixes or shell quoting. Transport selection and ticker/rollover constants read process environment directly; export those options in the launching shell.

Preferred variables:

- `HERMES_TELEGRAM_BOT_TOKEN`
- `HERMES_TELEGRAM_CHAT_ID`

Fallback variables:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_HOME_CHANNEL`
- `TELEGRAM_USER_ID`

Optional:

- `HERMES_TASK_MONITOR_TICK=10`
- `HERMES_MONITOR_LANE=default`
- `HERMES_TASK_MONITOR_DISABLED=true`
- `HERMES_TASK_MONITOR_FORCE_ENABLE=true`
- `HERMES_TASK_MONITOR_TRANSPORT=telegram|whatsapp`
- `HERMES_WHATSAPP_CHAT_ID=...`
- `HERMES_WHATSAPP_BRIDGE_URL=http://127.0.0.1:3000`
- `HERMES_TASK_MONITOR_WHATSAPP_ROLLOVER=840`

## Agent Skill

The reusable skill is included at:

```text
skills/task-monitor/SKILL.md
```

Copy that folder into the agent skill directory used by your runtime, or point your agent at this repo and ask it to follow `AGENTS.md`.

## State

Runtime monitor state is stored locally at:

```text
~/.openclaw/task-monitors/
```

Do not commit this folder. It contains live task state, message IDs, and local operational history.

## Agent Quick Start

When another user gives this repo link to an agent, the expected flow is:

```bash
git clone https://github.com/kofiowusuai-lab/task-monitor-agent.git
cd task-monitor-agent
chmod +x bin/task-monitor
mkdir -p ~/.local/bin ~/.openclaw
ln -sf "$PWD/bin/task-monitor" ~/.local/bin/task-monitor
cp .env.example ~/.openclaw/.env
```

Then the user fills in their own Telegram credentials. Agents should launch a monitor before multi-step work and keep the same monitor updated until the task is verified complete or hard-blocked.

## Safety

- Do not commit `.env*`, monitor JSON state, locks, logs, or transport credentials.
- Never mark a stage `done` until the underlying work is actually verified.
- If the selected transport is rate-limited or unavailable, continue the work and report that the visibility layer failed.

## Parallel lanes and routing

Stages describe sequential work; lanes track independent workers:

```bash
task-monitor lane "$ID" Builder active --detail "Implementing the change"
task-monitor lane "$ID" Builder done --detail "Validation passed"
task-monitor lanes-done "$ID"
task-monitor finish "$ID" --fail --summary "Blocked by unavailable provider"
```

`lanes-done` exits successfully when every lane is settled as done or failed. `start --task` supplies an explicit deduplication key; a matching live task can reuse its card. Use `--force` only when a separate card is intentional. `launch` is an alias for `start`. Run `task-monitor --help` or a subcommand's `--help` for its arguments.

[`bin/lane_route.py`](bin/lane_route.py) optionally reads `~/.openclaw/telegram_routes.json`: each lane maps to an object with `token` and `chat` keys. Select a route with `start --lane` or `HERMES_MONITOR_LANE`. Lane entries take priority over `HERMES_TASK_MONITOR_OVERRIDE_TOKEN` / `HERMES_TASK_MONITOR_OVERRIDE_CHAT`, then the normal Telegram variables. `TELEGRAM_CHAT_ID` is also accepted as a fallback. WhatsApp additionally accepts `WHATSAPP_HOME_CHANNEL` and `WHATSAPP_BRIDGE_URL`. Keep routing files private because they contain credentials.

## Implementation and verification

[`bin/task-monitor`](bin/task-monitor) owns CLI parsing, transport requests, JSON state, locked updates and the detached ticker. Telegram uses the Bot API; WhatsApp uses bridge `POST /send` and `POST /edit` endpoints. The ticker refreshes the elapsed display, but only real stage/detail updates count as progress. A quiet card can therefore show a stalled footer. Known Recorrido support-inbox polling titles are deliberately stored as silent monitors without visible messages.

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 bin/task-monitor --help
```

The tests cover silent poll handling and WhatsApp requests/rollover with mocks and a local HTTP server. They require no live Telegram or WhatsApp credentials. Runtime artifacts are monitor JSON files and lock files under `~/.openclaw/task-monitors/`, plus a background ticker process for visible cards.

## Troubleshooting

- `command not found`: add `~/.local/bin` to `PATH`, or invoke `python3 bin/task-monitor` directly. Keep `bin/lane_route.py` next to the real CLI file when installing.
- Missing credentials or unexpected routing: check both env files and any lane route; file configuration may override an exported token/chat.
- Disabled profile: check `HERMES_TASK_MONITOR_DISABLED`. Explicit enablement uses `HERMES_TASK_MONITOR_FORCE_ENABLE` or the local `~/.openclaw/task-monitor.enabled` marker.
- Delivery errors: inspect foreground stderr and use `show` to inspect the saved card. Telegram rate limits receive bounded retry handling; persistent transport errors can stop the ticker. A moving timer is not proof that the underlying task advanced.
- WhatsApp continuation cards are expected before the edit window expires. This transport maintains a task across multiple cards, rather than guaranteeing one physical message for its entire duration.

This repository monitors work; it does not execute, supervise or verify the underlying build. Agents must supply truthful stage updates and explicitly finish their task.
