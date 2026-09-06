# HydraHive feature inventory

This document records the user-visible and operator-facing feature surface implemented in the current HydraHive core repository and its official module hub.

It is an inventory, not a claim that every feature is active on every installation. Availability depends on the authenticated role, installed modules, selected installer components, credentials, external services and hardware.

## Status labels

| Label | Meaning |
|---|---|
| **Core** | Implemented in the HydraHive core backend/frontend repository |
| **Module** | Distributed through the separate `hydrahive2-modules` hub; backend loads at runtime and frontend is compiled during installation/update |
| **Optional** | Implemented but unavailable until enabled or configured |
| **External dependency** | Requires a third-party API, service, account or executable |
| **Infrastructure-dependent** | Requires host capabilities such as libvirt, Incus, Docker, systemd or NVIDIA/CUDA |
| **Template** | Developer example rather than a production feature |

Primary verification sources:

- API assembly: `core/src/hydrahive/api/main.py`;
- frontend routes: `frontend/src/App.tsx`;
- navigation: `frontend/src/shared/nav-config.ts`;
- native tools: `core/src/hydrahive/tools/__init__.py`;
- runtime modules: `core/src/hydrahive/modules/`;
- service extensions: `extensions/manifests/*.json`;
- Linux provisioning: `installer/install.sh` and `installer/modules/`;
- official module catalog: `hydrahive2-modules/hub.json` and each module's `manifest.json` in the separate repository.

---

## 1. Agents and Buddy

**Status: Core**

- Personal Buddy created per user.
- Standalone agents, project agents and project specialists.
- Agent create/read/update/delete and enable/disable state.
- System prompt and editable agent Markdown files.
- Primary text model, ordered fallback models and optional compaction model.
- Temperature, output-token limit, reasoning effort, cache lifetime and maximum iterations.
- Native/plugin tool selection and MCP-server assignments.
- Optional confirmation before tool execution.
- Optional long-term memory and context-compaction controls.
- Agent activity stream and visual activity monitor.
- Specialist creation/configuration and AgentLink delegation.
- External AgentLink instances with generated API keys.

**Sources:** `core/src/hydrahive/agents/`, `core/src/hydrahive/buddy/`, `core/src/hydrahive/api/routes/agents.py`, `buddy.py`, `agent_activity.py`, `external_instances.py`, `frontend/src/features/agents/`, `frontend/src/features/buddy/`.

### Skills

**Status: Core**

- Markdown-based skills with name, description, activation guidance and body.
- Global, project and specialist scopes.
- Per-agent disabled-skill lists.
- List/load/create/update/delete tools for agents.
- System-default skills shipped with the core.

**Sources:** `core/src/hydrahive/skills/`, `core/src/hydrahive/tools/list_skills.py`, `load_skill.py`, `write_skill.py`, `delete_skill_tool.py`, `frontend/src/features/skills/`.

---

## 2. Chat and run lifecycle

**Status: Core**

- Streaming assistant output through Server-Sent Events.
- Text and file attachments, including image content blocks.
- Tool-use and tool-result cards with live status.
- User approval/denial for confirmation-gated tool calls.
- Server-side run task that can continue after the original browser request disconnects.
- Reattachment to a running session, run-status polling and explicit cancellation.
- Resend from an earlier message and continue after a paused iteration limit.
- Session title/status update, project association and deletion.
- Per-session text-model and reasoning-effort overrides.
- Project picker and project-bound chat.
- Workspace file viewer/editor and Git panel beside the chat.
- Message search, pagination and generated-media previews.
- Voice input plus browser/local/MiniMax/OpenRouter speech output paths.
- Hydra emotes.
- Local slash commands: `/help`, `/clear`, `/model`, `/compact`, `/tokens`, `/title`, `/system`, `/tools`, `/skills`, `/agent`, `/export` and direct skill invocation.

HydraHive currently does not expose the earlier documentation's archive/tag/fork workflow as core session API operations; the implemented session operations are defined in `sessions.py` and `sessions_messages.py`.

**Sources:** `core/src/hydrahive/api/routes/sessions.py`, `sessions_messages.py`, `core/src/hydrahive/runner/`, `frontend/src/features/chat/`.

### Runner protections

- Primary-to-fallback model routing.
- Maximum-iteration pause.
- Repeated-tool-loop detection.
- Explicit error for empty model output.
- Explicit failure for tool arguments truncated by the output-token limit.
- Tool-result character limits and history compaction.
- Healing of incomplete tool-use sequences.
- Persisted token/cache/model metadata and estimated cost per LLM call.

**Sources:** `core/src/hydrahive/runner/runner.py`, `_runner_iter.py`, `_runner_tools.py`, `core/src/hydrahive/compaction/`, `core/src/hydrahive/db/llm_calls.py`.

---

## 3. Native tools, MCP and plugins

**Status: Core; tool availability is agent-specific**

The core registry includes tool families for:

- shell execution and workspace file read/write/patch;
- web search, authenticated HTTP fetch and browser automation;
- memory read/write/search and session observations;
- session data mining and timelines;
- email read/send;
- project, specialist and skill management;
- agent-to-agent delegation when AgentLink is configured;
- image analysis and image/music/speech/video generation;
- audio transcription;
- prompt archive access;
- code-graph query/explain/path/impact/refresh;
- Webmin status and generic RPC when configured.

Installed modules can contribute additional tools. Current official examples include Home Assistant, Crypto, Mediacenter, Deep Research, Patientenakte, Scratchpad, Tasks and Atelier tools.

### MCP

- MCP server configuration and per-agent assignment.
- Schemas discovered from selected servers and merged with native/plugin schemas.
- stdio, streamable HTTP and SSE transport support as defined by the MCP client implementation.

### Plugins

- Plugin-hub cache plus validated `plugin.yaml` manifests under `HH_DATA_DIR/plugins`.
- Dynamic tool schemas assigned to agents.
- Plugin install/update/uninstall management.
- Per-plugin discovery/load error isolation.

The loader imports plugin Python and calls `on_load(ctx)` inside the backend process. There is no subprocess or OS sandbox; installed plugin code is fully trusted code.

**Sources:** `core/src/hydrahive/tools/__init__.py`, `core/src/hydrahive/mcp/`, `core/src/hydrahive/plugins/`, `core/src/hydrahive/api/routes/mcp.py`, `plugins.py`.

---

## 4. Memory, compaction and data mining

### Agent memory

**Status: Core; semantic recall requires the PostgreSQL mirror and embeddings**

- Per-agent observation log.
- Persistent memory notes with key, content, project scope, confidence, expiry and supersession behavior.
- Full-text-like local memory search.
- Memory cards in the optional PostgreSQL mirror.
- Proactive top-card recall and cue-triggered semantic recall when long-term memory is enabled.
- Background session compression and memory crystallization/consolidation.
- Manual memory inspection and curation page.

**Sources:** `core/src/hydrahive/tools/_memory_*.py`, `read_memory.py`, `write_memory.py`, `search_memory.py`, `_observations.py`, `core/src/hydrahive/cards/`, `core/src/hydrahive/db/_mirror_cards*.py`, `frontend/src/features/memory/`.

### Context compaction

- Context-window-aware threshold.
- Separate compaction model.
- Configurable reserve, retained turns and tool-result limit.
- Persisted compaction events.
- Manual `/compact` command and pre-resume compaction.

**Sources:** `core/src/hydrahive/compaction/`, `core/src/hydrahive/db/compaction_events.py`, `core/src/hydrahive/runner/runner.py`.

### Data mining

**Status: Optional PostgreSQL mirror**

- Recent event view.
- Full-text and semantic event search.
- Session listing/detail and event topology graph.
- Embedding status, reset, rechunk and backfill.
- Imports from HydraHive SQLite, Git, JSONL, nginx/journal logs and uploaded shell history.
- GitHub issue/PR event import.
- Daily, latest-session, per-session and per-agent token statistics.
- Agent tools for semantic search, full-text search, timeline and daily summary.

**Security boundary:** the current data-mining endpoints require authentication, but the route layer is not generally scoped to the caller's own username and some queries accept an explicit username filter. Treat this as a sensitive shared analytics surface and restrict user access at deployment level until finer-grained authorization is implemented.

**Sources:** `core/src/hydrahive/api/routes/datamining*.py`, `core/src/hydrahive/db/_mirror*.py`, `core/src/hydrahive/tools/datamining*.py`, `frontend/src/features/datamining/`.

---

## 5. Projects and engineering workspaces

**Status: Core**

- Project create/read/update/delete.
- Creator plus members with project-specific `read`, `write` and `admin` roles; the creator has implicit project-admin access.
- Project audit log.
- Project sessions and aggregate statistics.
- Project agent and specialists.
- Isolated project workspace.
- File tree, read, write, upload and delete.
- Multiple repository folders with Git initialize/clone/configure/status/diff/commit/pull/push/remove operations.
- Gitea repository creation and push/pull integration.
- Samba workspace share configuration.
- SMB mount registry and per-project assignment.
- VM/container assignment to projects.
- Project integrations for MCP IDs, allowed plugins and project LLM key.
- Project-bound persistent tasks through the required Tasks module.

The current Tasks panel supports create, priority and status transitions. The core repository does not contain the previously documented project-task comments or GitHub issue synchronization subsystem.

**Sources:** `core/src/hydrahive/projects/`, `core/src/hydrahive/api/routes/projects*.py`, `smbmounts.py`, `frontend/src/features/cockpit/project/`, `modules/tasks/`.

### Code graph

**Status: Core; requires a project build**

- Select scan directories inside a project.
- Build a local graph with metrics and cycle report through the `graphify` binary.
- Query, explain, shortest path and reverse impact traversal from agent tools.
- Refresh after source changes.

The graph reflects its last successful build; it is not updated automatically after every edit.

**Sources:** `core/src/hydrahive/code_graph*.py`, `core/src/hydrahive/api/routes/code_graph.py`, `core/src/hydrahive/tools/code_graph_tools.py`, `frontend/src/features/cockpit/project/ProjectGraphOverlay.tsx`.

---

## 6. Models and providers

**Status: Core; credentials/local runtime required**

The current provider catalog/configuration has explicit entries for:

- Anthropic;
- OpenAI;
- OpenAI Codex OAuth;
- OpenRouter;
- Groq;
- Mistral;
- Google Gemini;
- NVIDIA NIM;
- MiniMax;
- Ollama-compatible local or protected endpoints.

Models from other vendors can still appear through aggregators such as OpenRouter or NVIDIA NIM; that is not the same as a dedicated direct-provider adapter.

Capabilities:

- live provider model listing where an endpoint exists;
- static fallback models for selected providers;
- model purpose classification for chat, embeddings, speech, transcription, image, video and music;
- context-window, tool-use, category and parameter metadata where known;
- pricing/usage estimates;
- canonical model registry with cache and incomplete-fetch handling;
- provider keys, base URLs, group IDs and OAuth paths;
- model tool-support gate;
- per-agent and per-session selection.

**Sources:** `core/src/hydrahive/llm/_catalog_data.py`, `catalog.py`, `registry.py`, `_config.py`, `client.py`, `core/src/hydrahive/oauth/`, `frontend/src/features/llm/`.

### Ollama

- Live model catalog and capabilities.
- Pull, running-model and delete/lifecycle management.
- Context-size selection with VRAM-aware cap.
- `llmfit` hardware-fit information when installed.

**Sources:** `core/src/hydrahive/llm/ollama_*.py`, `core/src/hydrahive/api/routes/llm_catalog_ollama.py`, `installer/modules/35-llmfit.sh`.

---

## 7. Generated media and Media Cockpit

### Agent media tools

**Status: Core; OpenRouter or configured local backend required**

- Vision/image analysis.
- Text-to-image and reference-image generation.
- Optional green-screen chroma key for transparent image output.
- Text-to-music generation.
- Text-to-speech.
- Text/image-to-video asynchronous jobs.
- Audio transcription.
- Generated files saved in the active workspace and previewed in chat.

**Sources:** `core/src/hydrahive/tools/analyze_image.py`, `generate_image.py`, `generate_music.py`, `generate_speech.py`, `generate_video.py`, `transcribe_audio.py`.

### Prompt archive

- Categories for image, music, system, video, speech and other prompts.
- Prompt text, fixed style anchor, model, params, seed, tags, notes and sample path.
- User-owned/private and public entries.
- List/get/save agent tools.

**Sources:** `core/src/hydrahive/db/prompt_archive.py`, `core/src/hydrahive/api/routes/prompt_archive.py`, `core/src/hydrahive/tools/prompt_archive.py`.

### Media Cockpit

**Status: Core project workspace; generation workflows depend on installed modules/backends**

- Media projects bound to HydraHive projects.
- Idea/brief, prompts, screenplay with acts/scenes/shots, references and assets.
- Workspace file browsing and media asset registration.
- Timeline tracks, transitions and export library.
- Video cut/assembly operations.
- Pluggable `mediaSources` and `mediaWorkflows` contributed by modules.

**Sources:** `core/src/hydrahive/media_*.py`, `core/src/hydrahive/api/routes/media_*.py`, `frontend/src/features/cockpit/MediaCockpitPage.tsx`, `frontend/src/features/cockpit/media/`.

### Local media backend

**Status: Optional; NVIDIA/CUDA and Docker required by automated installer**

- ComfyUI and switch-HTTP backend registry.
- Workflow import/parser with parameter mapping.
- Local image/video model IDs (`local:` routing).
- Automated ComfyUI Docker setup on NVIDIA hosts.
- Installer registers SDXL image, Wan text-to-video and Wan first/last-frame workflows.

The local-media installer downloads large third-party models and validates pinned SHA-256 hashes. No compatible NVIDIA GPU means the phase is skipped.

**Sources:** `core/src/hydrahive/api/routes/media_backends.py`, `core/src/hydrahive/llm/video_backends/`, `installer/modules/72-local-media.sh`, `installer/media-workflows/`.

---

## 8. Butler automation

**Status: Core; modules can contribute node types**

- Flow create/read/update/delete.
- Graph of trigger, condition and action nodes.
- User or project scope.
- Dry-run execution.
- Project webhook trigger with optional project secret.
- Runtime registry extended by modules.
- Supervised periodic module jobs.
- Cryptoboard contributes price/alert pollers plus Butler trigger/condition types.

The webhook route retains a deprecated compatibility path when a project has no configured secret. Configure a secret before exposing project webhooks.

**Sources:** `core/src/hydrahive/butler/`, `core/src/hydrahive/api/routes/butler.py`, `core/src/hydrahive/modules/context.py`, `frontend/src/features/butler/`, `hydrahive2-modules/cryptoboard/backend/__init__.py`.

---

## 9. Communication, voice and research

### WhatsApp

**Status: Optional bridge**

- Node bridge installation and secret.
- Pairing/status, chats/messages and inbound processing.
- Text/media handling and voice conversion support.
- Route and runtime health management.

**Sources:** `core/src/hydrahive/communication/whatsapp/`, `core/src/hydrahive/api/routes/communication_whatsapp*.py`, `installer/modules/45-whatsapp.sh`.

### Discord

**Status: Optional bot**

- Bot configuration, enable/disable state and message bridge.

**Sources:** `core/src/hydrahive/communication/discord/`, `core/src/hydrahive/api/routes/communication_discord*.py`.

### Matrix team chat

**Status: Optional Matrix homeserver**

- Team-chat rooms/messages and authenticated API.
- Tuwunel can be installed separately from the extension catalog.

**Sources:** `core/src/hydrahive/teamchat/`, `core/src/hydrahive/api/routes/teamchat.py`, `core/src/hydrahive/settings/_teamchat.py`.

### Mail

**Status: Optional IMAP/SMTP**

- Agent tools to read mail without marking it read and to send plain-text mail.
- Global defaults plus tool-specific credential configuration.
- Optional incoming-mail watcher/Butler integration.

**Sources:** `core/src/hydrahive/tools/read_mail.py`, `send_mail.py`, `core/src/hydrahive/settings/_mail.py`, `core/src/hydrahive/communication/mail/watcher.py`.

### Voice

**Status: Core STT/TTS APIs plus optional install/module**

- Browser voice input and browser/local/cloud voice output in chat.
- Core STT and TTS endpoints.
- Installer can provision Wyoming Faster Whisper and Wyoming Piper in Incus; it also installs the optional MiniMax `mmx` CLI.
- Official Voice module provides a Voicebox for the Home Assistant Voice PE path.

**Sources:** `core/src/hydrahive/api/routes/stt.py`, `tts.py`, `core/src/hydrahive/voice/`, `frontend/src/features/chat/useVoice*.ts`, `installer/modules/55-voice.sh`, `hydrahive2-modules/voice/`.

### Research APIs

- Configurable research API profiles.
- Deep Research module performs multi-step web research and returns a cited report.

**Sources:** `core/src/hydrahive/research/`, `core/src/hydrahive/api/routes/research_apis.py`, `hydrahive2-modules/deepresearch/`.

---

## 10. Infrastructure

### Compute nodes and jobs

**Status: Core; remote node agent required**

- Node enrollment/bootstrap, recovery result and certificate lifecycle.
- mTLS-protected compute-agent connection through the standard nginx edge.
- Heartbeats, node health, sequence/nonce checks and audit records.
- Remote command/job queue and console tickets.
- CPU/RAM/storage/GPU inventory where reported.
- Placement fields for VM/container runtimes.

**Sources:** `core/src/hydrahive/compute/`, `core/src/hydrahive/api/routes/compute_*.py`, `node-agent/`, `installer/modules/60-nginx.sh`.

### Virtual machines

**Status: Infrastructure-dependent**

- VM create/list/update/delete.
- Start, stop, restart, pause, resume, shutdown and force actions.
- ISO upload/list/delete.
- Disk import and passthrough.
- Snapshot lifecycle.
- Browser VNC tickets/proxy.
- Local or compute-node runtime placement.

**Sources:** `core/src/hydrahive/vms/`, `core/src/hydrahive/api/routes/vms*.py`, `frontend/src/features/vms/`, `installer/modules/65-vms.sh`.

### Containers

**Status: Infrastructure-dependent**

- Incus container create/read/update/delete.
- Start, stop, restart and snapshot operations.
- Browser terminal/WebSocket console.
- Local or compute-node placement.

**Sources:** `core/src/hydrahive/containers/`, `core/src/hydrahive/api/routes/containers*.py`, `frontend/src/features/containers/`, `installer/modules/70-containers.sh`.

### Federation and Tailscale

- Workstation registry with cached A2A cards and remote audit retrieval.
- TLS verification enabled by default per workstation, with explicit opt-out for self-signed LAN/Tailnet peers.
- Client-config generator combining a HydraHive API key, AgentLink coordinates and optional Tailscale invitation.
- Tailscale status/setup endpoints and optional installer phase.

**Sources:** `core/src/hydrahive/federation/`, `core/src/hydrahive/api/routes/federation.py`, `tailscale.py`, `core/src/hydrahive/tailscale/`, `installer/modules/80-tailscale.sh`.

---

## 11. Official module hub

**Status: Separate repository; install/update rebuilds the frontend and requests a backend restart**

The official hub currently contains **18 entries**:

```text
18 directories with manifest.json
= 17 end-user modules + 1 example template
```

| Module | Current manifest version | Capability | Agent/runtime contributions |
|---|---:|---|---|
| Archiver | 2.0.2 | archives web pages, forum threads and documents; jobs, drive status, diagnostics, repair/export | router, migration |
| Atelier | 1.6.5 | project-bound image/video/music/film production with characters, screenplay, shots, gallery and composition | read/write tools; depends on Video Editor |
| Blueprint | 1.0.2 | visual node canvas for layouts and workflows | router, migration |
| Brettspiele | 1.0.2 | browser board games including chess and result storage | routers, migration, Buddy widget |
| Cryptoboard | 1.1.2 | prices, charts, watchlist, portfolio/trades, CSV import, wallets, alerts, indicators and news | 3 tools, Butler types, 2 poll jobs, migration |
| Deep Research | 1.0.2 | multi-stage, source-backed research reports | `research_report` tool, router, migration |
| Haushaltsbuch | 1.5.3 | household members, ledger, budgets/planning, bank import and experimental read-only Lidl Plus receipt sync | routers, migration |
| Home Assistant | 1.0.2 | list/read entities, render templates and call services | 4 tools, router, migration |
| Mediacenter | 0.8.1 | profile-filtered Treasure Maps search and controlled SABnzbd queue/history | 5 tools, routers, migration |
| Minigames | 1.0.2 | small browser games and high scores | router, migration, Buddy widget |
| Musicplayer | 1.0.1 | playlist/equalizer for generated and uploaded music | routers, migration, Buddy widget |
| Notizbuch | 1.0.2 | user notes | CRUD router, migration |
| Meine Akte | 1.0.2 | structured record, eGA/FHIR imports and Apple Health views | 2 read tools, routers, migrations, Buddy widget |
| Scratchpad | 1.0.2 | separate user and agent note zones | 2 tools, router |
| Aufgaben | 1.0.1 | persistent tasks across sessions and optional project relation | 4 tools, router, migration, Buddy/workspace UI |
| Video-Editor | 0.1.2 | browser timeline, trimming and hybrid export | router; dependency of Atelier |
| Voice | 0.8.0 | Voicebox/HA Voice PE assistant settings, transcript, STT/TTS and speech | routers |
| Beispiel-Modul | 1.0.1 | minimal developer example | template router and migration |

Versions and descriptions above are taken directly from the module manifests at the time of this inventory. The installed version can differ until the administrator updates it.

### Module lifecycle

- The default hub URL is `https://github.com/hydrahive/hydrahive2-modules.git`.
- Additional comma-separated hub URLs can be configured; the first module ID wins when hubs overlap.
- Hub operations use a local shallow Git cache and a 15-second Git command timeout.
- Installation copies the full module to `HH_DATA_DIR/modules/<id>` and its frontend to `frontend/src/modules/<id>`.
- Dependencies are installed first.
- The frontend is rebuilt, then a delayed restart request is written.
- Uninstall removes module files but deliberately retains module database tables/data.
- A broken module load is isolated from other modules.
- The Tasks module is required by core cockpit features and is repaired from the bundled source when absent or incomplete.

**Sources:** separate repository `hub.json` and `*/manifest.json`; core `core/src/hydrahive/modules/hub_client.py`, `installer.py`, `loader.py`, `context.py`.

---

## 12. Service extensions

**Status: Core admin lifecycle; each third-party service is optional**

The core repository contains **32 extension manifests**, calculated as:

```text
find extensions/manifests -name '*.json' → 32 files
```

Related local assets:

```text
29 install scripts
29 uninstall scripts
5 Docker Compose files
```

Catalog by category:

- **AI:** AnythingLLM, Ollama, Skill Seekers;
- **development:** Go, Java 21, Node.js, Rust;
- **tools:** Code Server, Gitea, SearXNG, ShadowBroker;
- **network:** AdGuard Home, Headscale, Pi-hole, Tuwunel;
- **security:** Vaultwarden;
- **productivity:** BookStack, Mailcow, Monica CRM, Radicale, Vikunja;
- **media:** Plex, Radarr, SABnzbd, Sonarr;
- **gaming:** HyOS, Minecraft, TrinityCore 3.3.5a, Valheim;
- **dashboard/documents/system:** Heimdall, Paperless-ngx, Webmin.

These are installation/integration descriptors for third-party software. They are not installed by default and are not covered by HydraHive's license. Extension actions can invoke privileged shell or Docker operations and therefore require administrator trust.

**Sources:** `extensions/manifests/`, `extensions/install/`, `extensions/uninstall/`, `extensions/docker/`, `core/src/hydrahive/api/routes/extensions.py`.

---

## 13. Additional core and module work areas

### Core work areas

- **Dashboard:** local summary cards including system/agent/project/token information.
- **Project Cockpit:** dense project chat, agents, Git, files, tasks and management overlays.
- **Buddy Cockpit:** personal assistant and installed Buddy widgets.
- **Media Cockpit:** media project preparation and post-production.
- **Vault Cockpit:** offline-first launchpad for Patientenakte, Cryptoboard, Scratchpad, Credentials, Data Mining and Memory.
- **Admin Cockpit:** users, LLM, MCP, credentials, modules, themes, plugins, extensions, VMs, containers, nodes/jobs and system links.
- **Communication, Teamchat, Butler, Federation, Streaming, Data Mining, Memory, Zahnfee and Help** pages.

The current Vault is a launchpad/soft guard. It does not yet implement the displayed future 15-minute hard lock, merged document/OCR store or automatic AI analysis. Those items are explicitly shown as roadmap in `VaultCockpitPage.tsx`.

### Streaming downloader

**Status: Core, specialized external dependency**

- encrypted per-user Ghostflix credentials;
- series scrape;
- selected episode download jobs;
- output path targeting a Plex library;
- job list, cancellation and deletion.

**Sources:** `core/src/hydrahive/api/routes/streaming.py`, `core/src/hydrahive/streaming/`, `frontend/src/features/streaming/`.

### Zahnfee

**Status: Core, administrator route**

Dental laboratory/order workflow exposed through its own backend and frontend feature.

**Sources:** `core/src/hydrahive/zahnfee/`, `core/src/hydrahive/api/routes/zahnfee.py`, `frontend/src/features/zahnfee/`.

---

## 14. Administration, settings and lifecycle

**Status: Core; privileged actions are administrator-only where guarded by API**

- User create/list/update/delete and API-key management.
- Global system overrides and mail defaults.
- Provider, model, OAuth, MCP, credential and research-API configuration.
- Module, theme, plugin and service-extension management.
- System info, application/storage statistics and health checks.
- Update check, update request, restart request and update logs.
- Voice, network-bridge and Samba setup requests/logs.
- Backup and restore.
- Server-to-server migration state/start/log.
- Dashboard and analytics, including per-session trace and token/cost data.

**Sources:** `core/src/hydrahive/api/routes/system*.py`, `users.py`, `backup.py`, `migration.py`, `analytics.py`, `dashboard.py`, `frontend/src/features/system/`, `frontend/src/features/cockpit/admin/`.

### API documentation

OpenAPI/Swagger is disabled by default. Set:

```text
HH_ENABLE_DOCS=true
```

and restart the backend to expose:

```text
/api/docs
/api/openapi.json
```

The API is intentionally namespaced under `/api`, including runtime module routers at `/api/modules/<module-id>`.

**Source:** `core/src/hydrahive/api/main.py`.

---

## 15. Installation and deployment

**Status: Linux primary; macOS installer exists with reduced host-infrastructure parity**

The interactive Linux installer can provision:

- Python 3.12, Node.js 20, ffmpeg, `uv/uvx`, GitHub CLI and mmx CLI;
- dedicated service user and filesystem permissions;
- Python environment and React build;
- `llmfit`;
- local ComfyUI media runtime on compatible NVIDIA systems;
- WhatsApp bridge;
- Samba project shares;
- PostgreSQL data-mining mirror;
- systemd application and helper timers;
- nginx HTTPS edge;
- QEMU/KVM/libvirt VM support;
- Incus containers;
- voice stack;
- HydraLink/AgentLink;
- Tailscale;
- initial LLM provider setup.

All component choices default to yes in non-interactive/no-saved-choice mode except where explicitly set otherwise. See [../installer/README.md](../installer/README.md) before installing on a multipurpose host.

**Sources:** `installer/install.sh`, `installer/modules/`, `installer/install-mac.sh`, `installer/update.sh`, `installer/migrate.sh`.

---

## 16. Authentication and security controls

Implemented controls include:

- bcrypt password hashing and lazy migration from legacy SHA-256;
- expiring HS256 JWTs and explicit API keys;
- immutable user IDs in the newer principal-based authorization path;
- admin role checks and final-admin demotion protection;
- login lockout/throttling support;
- AES-GCM encryption of credential values and restricted credential-file mode;
- project roles and project audit events;
- tool allowlists and confirmation gate;
- validated plugin manifests, explicit assignment and per-plugin load-failure isolation (but no plugin sandbox);
- nginx TLS, security headers, request limits and compute-node mTLS in the standard Linux deployment.

Important limitations:

- several legacy route dependencies still return username/role rather than immutable principals; each resource route must therefore be reviewed for its own ownership check;
- authenticated data-mining access is broader than per-user isolation;
- modules execute in the backend process and plugins are not a hardened sandbox;
- extension installation is privileged by design;
- the default certificate is self-signed;
- cloud providers and external integrations receive the data required for the selected operation.

See [../SECURITY.md](../SECURITY.md) and [SECURITY_THREAT_MODEL.md](SECURITY_THREAT_MODEL.md).

**Sources:** `core/src/hydrahive/api/middleware/`, `core/src/hydrahive/credentials/`, `core/src/hydrahive/projects/`, `installer/modules/50-systemd.sh`, `60-nginx.sh`.

---

## 17. Deliberate non-claims

This inventory does not claim:

- that every module or extension is installed by default;
- that every provider model listed in metadata is currently available to every account;
- that model/provider prices or context metadata override the provider's live contract;
- that local inference works without compatible hardware and sufficient RAM/VRAM;
- that macOS offers Linux virtualization/service parity;
- that the Vault already enforces a hard timeout lock;
- that all authenticated analytics are isolated per user;
- that generated content is accurate, safe or free of third-party rights;
- that medical, finance or crypto modules provide professional advice;
- that module/plugin boundaries protect against malicious installed code; both execute in the backend process;
- that beta APIs and persisted formats are stable.
