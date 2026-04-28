# Chat

## What is this?

The Chat is your main window to the agents. You can run any number of **sessions** in parallel — each is an independent conversation with one agent. Sessions are persisted in the DB and survive restarts. Responses arrive **live** as they are generated (streaming).

## What can I do here?

- **Start a new session** — directly with an agent or in a project context
- **Talk to the agent** — it uses tools (read files, run code, MCP servers, …) to perform tasks
- **Cancel a response** — stop button while streaming
- **Trigger compaction manually** — Compact button in the header
- **Watch token usage** — the header shows last turn (input/output/cache) and session total
- **Delete sessions** — trash icon in the right list
- **Switch tabs** between direct chats and project chats

## Key terms

- **Session** — a conversation, identified by UUID
- **Turn** — one user question + agent response (may include multiple tool iterations)
- **Iteration** — a single LLM call inside a turn
- **Compaction** — summarizing older messages to save tokens
- **Streaming** — response arrives token by token instead of all at once
- **Tool use** — the agent uses one of its tools (e.g. `file_read`)
- **Cache (⚡)** — Anthropic-provided, reused system-prompt tokens (90% cheaper)

## Step by step

### First conversation

1. Click **+ New** at the top of the session list
2. Pick **Direct chat**, an active agent, optionally a title
3. Click **Start**
4. Type a message, press Enter
5. Watch text appear live, tools being called, tool results flowing into the chat

### Start a session inside a project

1. Click **+ New**
2. Switch to **In project**
3. Pick a project — its project agent is automatically linked
4. All `file_*` tools now operate inside the project workspace

### Compact a long conversation

1. Watch the token counter — when you approach the threshold
2. Click **Compact** in the header
3. Older messages get summarized into a structured Markdown digest
4. The chat shows a **Compaction block** (orange) — clickable for details

### Stop a response

While the agent streams: a red **Stop** square replaces the Send button. Click → the Anthropic stream is aborted, history reloads.

## Common errors

- **`max_tokens (4096) reached`** — response was truncated. Fix: **Agents** → this agent → set Max Tokens to 8192 or higher.
- **`Loop detected`** — agent calls the same tool 3 times in a row. Safety against infinite loops. Tell the agent clearly to do something different.
- **`Orphaned session`** — the agent of this session was deleted. Delete the session or recreate the agent.
- **`messages.X.content.0.text.parsed_output: Extra inputs`** — automatically self-healed by our repair helper. If not: start a new session.
- **HTTP 502 / 500 from Anthropic** — temporary server hiccups. Try again.

## Tips

- **Use cache**: keep an agent's system prompt stable. Across repeated sessions a large part is cached at 10% the token cost.
- **Tool whitelist**: enable per agent only the tools it really needs. Reduces tool-selection hallucinations.
- **Use the project agent for code work**: the workspace isolation means it only "sees" files inside the project.
