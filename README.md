# task-monitor-agent

Local Telegram and WhatsApp progress monitor for agent workflows. It creates one message per task and edits that message as stages move from pending to active to done or failed.

It is useful for long builds, renders, deploys, multi-agent workflows, research passes, and production runs where the user should not stare at a silent terminal.

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

The monitor reads configuration from `~/.openclaw/.env`, `~/.hermes/.env`, and process env.

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
