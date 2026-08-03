---
name: task-monitor
description: One live Telegram or WhatsApp message that updates in place through task stages. Use for multi-step builds, renders, deployments, long automations, and agent workflows. Not for one-shot replies.
---

# Task Monitor

Use this skill when work will take multiple steps and the user needs visible progress.

## Rule

Launch the monitor before work starts. One user task gets one monitor. Keep updating the same monitor through retries, repairs, QA, and delivery.

## Commands

```bash
ID=$(task-monitor start "Landing page demo" \
  --stages "Plan,Build,Test,Deploy")
echo "$ID"
```

For a task monitored in WhatsApp:

```bash
ID=$(task-monitor start "Landing page demo" --transport whatsapp \
  --stages "Plan,Build,Test,Deploy")
```

WhatsApp cards automatically roll over before the platform's edit window expires. Continue using the same monitor ID. The CLI moves later edits and `finish` to the current card.

```bash
task-monitor stage "$ID" Plan done
task-monitor stage "$ID" Build active --detail "Implementing local harness"
task-monitor detail "$ID" "API smoke test passed"
task-monitor note "$ID" "Using local storage because no shared database is required"
task-monitor finish "$ID" --success --summary "Repo published and verified"
```

`finish` syntax is strict:

```bash
task-monitor finish "$ID" --success --summary "done"
task-monitor finish "$ID" --fail --summary "blocked by missing credentials"
```

## Status Values

`pending` | `active` | `done` | `failed`

## Discipline

- A stage is `done` only after the external check is complete.
- If a command fails, mark the relevant stage `failed` or keep it `active` with the error detail while repairing.
- Do not fabricate monitor IDs if the selected transport is unavailable.
- Do not create a second monitor for the same task unless the first one is explicitly finished.
- The monitor is a visibility layer, not proof of completion. Verify files, tests, builds, deploys, and URLs separately.
