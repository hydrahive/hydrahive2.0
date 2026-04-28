# MCP Servers

## What is this?

**MCP** = Model Context Protocol, Anthropic's standard for exposing external tools to LLMs. Instead of programming each tool in HydraHive2 yourself, you can attach **MCP servers** — they then provide tools (filesystem access, GitHub API, databases, …) the agent can use on top of our 13 core tools.

An MCP server can run via three transports:

- **stdio** — subprocess on your machine (e.g. via `npx` or `uvx`)
- **streamable HTTP** — external HTTP endpoint (modern, recommended for remote servers)
- **SSE** — Server-Sent Events (legacy)

## What can I do here?

- **Add server from template** — 8 preconfigured (Filesystem, Memory, Git, GitHub, Time, Fetch, SQLite, Sequential-Thinking)
- **Add custom server** — your own with custom command/URL
- **Connect / Disconnect** — `Connect` opens the connection and loads the tool list
- **Inspect tools** — every available tool with description
- **Edit** — adjust command, args, env vars
- **Activate / Deactivate** — status toggle
- **Delete**

## Key terms

- **Transport** — how server and client talk (stdio/HTTP/SSE)
- **Server ID** — internal handle, becomes part of tool names (`mcp__<id>__<tool>`)
- **Args** — command-line arguments for the server (e.g. allowed directories for filesystem)
- **Env** — environment variables (e.g. `GITHUB_PERSONAL_ACCESS_TOKEN` for GitHub server)
- **Headers** — HTTP headers for auth (HTTP/SSE only), e.g. `Authorization: Bearer ...`

## Step by step

### Filesystem server for project code

1. Click **Template**
2. Pick **Filesystem**
3. Path: e.g. `/home/till/claudeneu` (the directory the agent may see)
4. **Create** — server is configured
5. In the detail form: **Connect** — npx pulls the package on first use
6. 14 tools appear (`read_file`, `list_directory`, `search_files`, …)

### GitHub server with your token

1. **Template** → **GitHub**
2. Enter your PAT (Personal Access Token) — `ghp_...` or `github_pat_...`
3. **Create**, **Connect**
4. Tools like `search_repositories`, `get_issue`, `create_pull_request` get loaded

### Custom HTTP MCP server

1. **+ New**
2. ID, name, transport **HTTP**
3. URL: e.g. `https://your-server.com/mcp`
4. **Create**
5. Optionally add headers in the edit form for auth
6. **Connect**

### Attach a server to an agent

1. **Agents** → open agent
2. **MCP servers** section: check the desired servers
3. **Save**
4. In chat the agent now has the `mcp__<id>__<tool>` tools available

## Common errors

- **`Connection failed: [Errno 2] No such file or directory`** — `command` (e.g. `uvx` or `npx`) is not on PATH. Fix: install the tool (`pip install uv` for `uvx`, `apt install nodejs npm` for `npx`).
- **Server starts but lists no tools** — some servers need explicit args (e.g. allowed paths). Check the detail form.
- **GitHub server `401 Unauthorized`** — token lacks the right scopes. Need at least `repo`, `read:user`, `read:org`.
- **Tools don't appear in agent chat** — the agent must be linked to the server AND the server must be connected. Otherwise lazy-connect kicks in only at first tool call.

## Tips

- **Use a restricted filesystem path** — don't pass `/` as allowed-path, give the specific project folder
- **Sequential-Thinking server** for complex problems — gives the agent a "thinking sketch" capability
- **Memory server (official MCP)** is different from our internal `read_memory`/`write_memory` — it offers knowledge-graph features with relationships
- **Multiple servers per agent** are no problem, all tools come together
