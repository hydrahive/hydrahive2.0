# System

## What is this?

The System tab is your **diagnostics center**. Here you see at a glance whether everything is running, how many resources are used, and where data lives. Auto-refreshes every 10 seconds.

## What can I do here?

- **Health status** — DB, LLM, workspaces, disk
- **Live stats** — agents, projects, sessions, messages, tool calls, DB size
- **Paths** — where data, config, and DB live
- **Uptime** — since when the backend has been running

## Key terms

- **Health check** — automatic test per service. Green = OK, red = problem.
- **Compactions** — number of executed session compactions
- **Tool-call success rate** — how many tool calls succeeded

## Health checks in detail

| Check | What's tested | What to do if red |
|---|---|---|
| **DB** | SQLite file readable/writable | Check disk space, file permissions |
| **LLM** | LLM config exists + default model + provider | LLM tab → set config |
| **Workspaces** | `data/workspaces/` writable | Permissions, disk space |
| **Disk** | >5% free | Clean up or larger disk |

## Step by step

### When something doesn't work

1. Open the **System tab**
2. Check the health bar at the top — all four green?
3. If red: detail text gives a hint
4. Check backend log: `tail -f /tmp/hh2-backend.log`
5. If still problems → restart backend via `dev-start.sh`

### Watch storage usage

- **DB size** — grows with every message. Slow at thousands of messages (DB VACUUM coming later).
- **Tool calls** — many tool calls benefit from compaction (Chat → Compact button)

## Common errors

- **DB red with `disk full`** — disk full, free space
- **LLM red with `No default model`** — LLM tab → pick model, save
- **Workspaces red with `Directory missing`** — backend started without write rights, restart with correct ENV vars

## Tips

- **Delete old sessions** when no longer needed — shrinks the DB
- **System tab as first stop** when there are issues — usually the answer is visible there
- **Auto-refresh leverages itself** — multiple browser tabs on System don't track anything extra, one tab is enough
