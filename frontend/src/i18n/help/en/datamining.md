# Datamining — search what your agents have done

## What is this?

Datamining is your **archive and magnifying glass** for everything that happened
in HydraHive: every conversation, every tool call, every session. You can search
it, trace histories, and analyze how much was "worked" (and consumed).

In short: normal chat shows you the *now* — datamining shows you the *entire past*,
searchable.

## The tabs

### Live feed
A live stream of current events — you see in near real time what the agents are
doing right now (messages, tool calls). Good for watching operations live.

### Search
Full-text search across **all** conversations. You can:
- filter by a **search term**,
- restrict by **event type** (e.g. only user inputs, only tool calls),
- turn on **semantic search** — then it searches not just for exact words but for
  **meaning similarity** (finds relevant things even when other words were used).

### Sessions
The list of all past **sessions** with date, agent, and user. A click opens the
detail view with all the session's **events** — handy to read a complete history
step by step.

### Token statistics
Analysis of **consumption**: created/last active, message count, and token
metrics. Here you see which sessions were especially "expensive".

### Graph
A visual representation of relationships (e.g. sessions and the users involved).
Use **Load graph** to build the view.

## Import

Via the **Import** function you can bring additional data sources into the archive
(e.g. from extensions/issues). If an import is configured, you see the status
**Mirror active**.

## Step by step: find something from the past

1. Open the **Search** tab.
2. Enter a search term — if your memory is fuzzy, turn on **semantic search**.
3. Optionally restrict the **event type**.
4. Click a hit → view the related session in detail in the **Sessions** tab.

## Common questions

- **"When did we talk about X?"** → Search (semantic if needed), then open the
  session.
- **"Which session was so expensive?"** → **Token statistics** tab.
- **"What's the agent doing right now?"** → **Live feed**.
- **"Mirror inactive / not configured"** → The database mirror
  (`HH_PG_MIRROR_DSN`) isn't set up; that's a system setting.

## Tips

- **Semantic search** is your friend when you only vaguely remember.
- **Event-type filter** cuts out noise — e.g. only "user inputs" to quickly find
  the thread of conversation.
- **Check token statistics regularly** if you want to keep an eye on costs.
