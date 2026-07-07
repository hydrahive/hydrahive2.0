# Dashboard

## What is this?

The **dashboard** is your home page for a system overview: in **customizable tiles
(widgets)** it shows at a glance how your HydraHive is doing — system health, key
metrics, token usage, connections, running sessions, and servers. You can
**reorder and hide** the tiles so the things you care about most sit at the top.

## The widgets

- **System status** — quick health check (is the AI reachable, is the database
  running, are workspaces writable). Your first glance when something's off.
- **Key metrics** — the most important numbers: active sessions, tokens today, etc.
- **Token usage** — today's usage and cost, including cache usage. Useful to keep
  an eye on spending.
- **Connections** — status of **Tailscale** (secure networking) and **AgentLink**
  (agent-to-agent communication).
- **MiniMax usage** — consumption if you use MiniMax as a provider.
- **Sessions & agents** — your recent conversations and the existing agents, with a
  direct jump in.
- **Servers overview** — state of connected servers (if configured).

At the top a **update banner** also appears when a new version is available.

## Core terms

- **Agent** — an AI personality with its own model, tools, and role.
- **Session** — an ongoing or past conversation between you (or a trigger) and an
  agent.
- **Token** — the billing unit of language models; "tokens today" shows daily usage.
- **Widget** — a single dashboard tile.

## Customize the dashboard

The tiles can be **moved** and **hidden** via the controls on each tile (in the
**widget frame**). Your arrangement is stored **locally in the browser** — so it
persists on this device but is individual per browser/device.

## Step by step

### First tour
1. Check **System status** at the top — all green? Then the basics are running.
2. In **Sessions & agents**, open an existing conversation or view an agent.
3. Use the **left navigation** to jump into the work areas (Buddy, Workshop,
   Projects …).

### When something doesn't work
If **System status** shows a problem (e.g. AI unreachable), you'll find details and
settings under **System** or **LLM configuration**.

## Common questions

- **"Numbers look stale"** — The dashboard loads on open; a page refresh fetches
  the current state.
- **"A widget doesn't interest me"** — Hide it; the others move up.
- **"Where are detailed system stats?"** — On the **System** page (more depth than
  the compact dashboard).
- **"No agent / no session visible"** — On first start there's only the master
  agent; create more under **Agents**.

## Tips

- **Most important up top**: order the tiles so your most frequent glance (e.g.
  token usage or system status) is at the very top.
- **Watch token usage** if cost matters — the widget shows daily usage and cache
  savings.
- **System status first** for any issue — it tells you in seconds where it's stuck.
