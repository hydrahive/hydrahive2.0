# Agents

## What is this?

An agent is a **configuration** — not a running instance. It consists of: name, type, LLM model, tool whitelist, MCP server list, system prompt, and memory. The agent comes alive when you start a session — the runner reads the config and runs the tool loop.

HydraHive2 has three agent types:

- **Master** — one per user, auto-created on first login. Has all tools, no restricted workspace, your personal assistant.
- **Project** — one per project, auto-created when you create a project. Workspace is restricted to the project folder.
- **Specialist** — freely configurable for specific domains (code review, writing, research, …). Tool set adjustable.

## What can I do here?

- **Create new agent** with type, model, tools
- **Edit existing agents** — model, temperature, max-tokens, tools, MCP servers, system prompt
- **Activate / Deactivate** via status dropdown
- **Delete** — removes config + memory + workspace
- **Inspect memory** indirectly through the agent's tool calls

## Key terms

- **System prompt** — instructions the agent sees first. Defines personality and behavior.
- **Memory** — JSON file per agent (`agents/<id>/memory.json`). Agent reads/writes via `read_memory`/`write_memory`.
- **Workspace** — file-system area the agent operates in. Auto-created under `data/workspaces/{master|projects|specialists}/<id>/`.
- **Temperature** — 0.0 = deterministic, 1.0 = creative (default 0.7).
- **Max tokens** — output limit per response. Code generation needs 8000+, conversation 2000–4000.
- **Thinking budget** — extended-thinking tokens (Sonnet/Opus 4+ only). 0 = off.

## Step by step

### Create a specialist for code review

1. Click **+ New**
2. Type **Specialist**, model `claude-sonnet-4-6`, name `Code-Reviewer`
3. **Create** — default tools are empty for specialists
4. In the detail form: enable `file_read`, `file_search`, `dir_list`, `read_memory`
5. System-prompt editor: write exactly what to do, e.g.:
   *"You analyze code for security issues, performance problems, and code smells. Read the file first, then provide structured Markdown feedback."*
6. **Save**

### Add an MCP server to the master agent

1. Click the master agent in the list
2. **MCP servers** section: check the configured servers
3. **Save**
4. In chat the agent now has additional `mcp__<server>__<tool>` tools

### Restrict the tool set

1. Open agent
2. **Tools** section: enable only the tools the agent may use
3. Save — on next LLM call only these tools are visible to the agent

## Common errors

- **`Model '...' is not in the LLM configuration`** — add it under LLM config or pick a known one.
- **`Unknown tools`** — only happens when manually editing `config.json`.
- **Agent hallucinates capabilities** — tighten the system prompt, reduce tool list.
- **Agent infinite-loops** — loop detection kicks in after 3 identical calls; often caused by `max_tokens` too small.

## Tips

- **System prompt is the most important knob**. More specific = better. Add examples of desired behavior.
- **Don't keep the master agent too generic** — it benefits from a clear profile too ("You are my personal coding assistant…").
- **Use specialists from inside projects** via `ask_agent` (with AgentLink) — the master delegates specific tasks.
