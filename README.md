# HydraHive

**Self-hosted AI orchestration, project workspaces, persistent memory, automation and media production — in one extensible web cockpit.**

<p align="center">
  <a href="https://github.com/hydrahive/hydrahive2.0/actions/workflows/pytest.yml"><img src="https://img.shields.io/github/actions/workflow/status/hydrahive/hydrahive2.0/pytest.yml?branch=main&label=CI" alt="CI"></a>
  <a href="https://github.com/hydrahive/hydrahive2.0/releases"><img src="https://img.shields.io/github/v/release/hydrahive/hydrahive2.0?include_prereleases&label=release" alt="Release"></a>
  <img src="https://img.shields.io/badge/status-beta-orange" alt="Beta">
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/FastAPI-0.111%E2%80%930.136-009688" alt="FastAPI 0.111–0.136">
  <img src="https://img.shields.io/badge/React-19-61dafb" alt="React 19">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
</p>

> [!IMPORTANT]
> HydraHive is in **beta**. APIs and persisted configuration formats can still change. Back up the data and configuration directories before upgrades.

This README is a concise product overview. The code-backed capability list, dependencies, limitations and source references are in **[docs/FEATURES.md](docs/FEATURES.md)**.

---

## What HydraHive is

HydraHive is a self-hosted control plane for AI agents. It combines:

- a Python/FastAPI orchestration backend;
- a React web application for chat, configuration and operations;
- personal, project and specialist agents;
- isolated agent/project workspaces with files and Git;
- skills, native tools, MCP servers and local tool plugins;
- persistent memory, context compaction and optional cross-session data mining;
- media generation and project-bound post-production;
- optional communication, automation, virtualization and compute-node components;
- an official hub of installable end-user modules.

“Self-hosted” applies to the HydraHive control plane and its stored data. Requests sent to a configured cloud model, search service, MCP server, messenger or another integration leave the host according to that service's terms.

---

## Highlights

### Agents and resilient chat

- A personal **Buddy**, standalone agents, project agents and project specialists.
- Streaming chat with attachments, tool cards, confirmation gates, cancellation and reconnection to server-side runs.
- Primary and fallback models, per-session model/reasoning overrides and token/cache/cost telemetry.
- Iteration and repeated-tool-loop limits, context-aware compaction and resumable paused runs.
- Reusable global, project and specialist **skills**.
- Agent-to-agent delegation through **HydraLink/AgentLink**.

### Tools, memory and research

- Native tools for files, shell, web search/browser, authenticated HTTP, mail, media, projects, code graphs and more.
- Additional tools from configured MCP servers, installed plugins and modules.
- Persistent memory notes, observations, background consolidation and proactive recall.
- Optional PostgreSQL data-mining mirror with semantic/full-text search, timelines, event graph and imports.
- Deep Research module for multi-stage, source-backed reports.

### Projects and engineering workflows

- Project owners/members with project-specific roles, audit events and isolated workspaces.
- File browser/editor, uploads, SMB mounts, Samba shares and Git/Gitea operations.
- Project chat, agents, specialists and persistent Tasks-module board.
- Locally built code graph with query, explanation, shortest-path, impact and refresh tools.
- VM/container assignment plus session/statistics views in the Project Cockpit.

### Models and media

- Provider configuration for Anthropic, OpenAI, OpenAI Codex OAuth, OpenRouter, Groq, Mistral, Gemini, NVIDIA NIM, MiniMax and Ollama.
- Live/static model catalogs, capability/context metadata, purpose classification and pricing estimates.
- Ollama model lifecycle plus optional `llmfit` hardware guidance.
- Image analysis/generation, music, speech, transcription and async video generation.
- Optional local ComfyUI workflows for SDXL and Wan on NVIDIA/CUDA + Docker hosts.
- Media Cockpit, prompt archive, timeline/cut workflow and installable Atelier/Video Editor modules.

### Automation, communication and infrastructure

- Butler trigger/condition/action flows, dry runs and project webhooks.
- Optional WhatsApp, Discord, Matrix team chat, IMAP/SMTP mail and voice components.
- Compute-node enrollment, mTLS channel, health/resources and remote jobs.
- QEMU/libvirt VMs, Incus containers, browser VNC and container terminal.
- Federation/workstation registry and optional Tailscale client bootstrap.
- Backup/restore, self-update/restart helpers and server-to-server migration.

### Extensibility

- Runtime **modules** for UI, API routes, database migrations, tools, Butler types and background jobs.
- UI-only **themes** with generated registry and layout/CSS contributions.
- Agent-tool **plugins** loaded from validated manifests and exposed through the normal tool interface.
- Privileged service **extensions** for third-party software such as Gitea, Ollama, SearXNG, Plex or Vaultwarden.

The official module hub currently contains **18 manifests: 17 end-user modules plus one developer example**. The core service-extension catalog contains **32 manifests**. The calculation and full lists are documented in [docs/FEATURES.md](docs/FEATURES.md).

---

## Main workspaces

| Workspace | Purpose |
|---|---|
| **Project Cockpit** | project chat, agents, Git, files, tasks, members, mounts, servers and code graph |
| **Buddy Cockpit** | personal assistant and module-contributed widgets |
| **Media Cockpit** | idea, prompts, screenplay, characters/style/assets and timeline/export |
| **Vault Cockpit** | offline-first launchpad for sensitive records, crypto, notes, credentials, memory and data mining |
| **Admin Cockpit** | users, providers, MCP, credentials, modules, themes, plugins, extensions, VMs, containers, nodes/jobs and system actions |

The current Vault is a launchpad and soft guard; its UI explicitly labels hard timeout locking and consolidated document/OCR handling as future work. It does not silently run AI analysis when opened.

---

## Modules versus extensions

| Concept | Purpose | Location/contract |
|---|---|---|
| **Module** | End-user feature with optional backend, migrations, tools, jobs and frontend | installed under `HH_DATA_DIR/modules/<id>` from [`hydrahive2-modules`](https://github.com/hydrahive/hydrahive2-modules) |
| **Theme** | Frontend layout, CSS and visual variables | copied into `frontend/src/themes` and included at build time |
| **Plugin** | Agent tool package | installed under `HH_DATA_DIR/plugins/<name>` with a plugin manifest |
| **Extension** | Third-party service/system package | `extensions/manifests/*.json` plus install/uninstall/Compose assets |

Installing or updating a module copies its backend/runtime files, copies its frontend into the core source tree, rebuilds the frontend and requests a backend restart. Uninstall removes module files but deliberately leaves module database data in place.

Extensions are different: their installers can use privileged shell or Docker operations. Treat every extension as reviewed administrator-trusted code.

---

## Quick start

### Linux

The primary installer targets a dedicated apt-based Ubuntu/Debian host. The repository has explicit upgrade handling for Ubuntu 24.04 and 26.04. On other releases, verify Python 3.12 and host-component compatibility first.

```bash
git clone https://github.com/hydrahive/hydrahive2.0.git
cd hydrahive2.0
sudo bash installer/install.sh
```

The interactive wizard can install:

- the FastAPI backend, React build, service account and systemd unit;
- nginx with a self-signed HTTPS certificate;
- HydraLink/AgentLink;
- PostgreSQL data mining;
- WhatsApp, Samba, voice and Tailscale;
- QEMU/libvirt VMs and Incus containers;
- NVIDIA local-media runtime when compatible hardware is detected.

Most optional components default to **yes** when no choice has been saved. Review [installer/README.md](installer/README.md) before running non-interactively on a multipurpose server.

At completion the installer prints:

```text
URL:       https://<server-ip>
Benutzer:  admin
Passwort:  <generated value>
```

The certificate warning is expected until the generated certificate is trusted or replaced. The backend itself binds to loopback by default.

### macOS

An experimental native installer exists:

```bash
bash installer/install-mac.sh
```

Linux-only systemd, libvirt, Incus and nginx provisioning does not have automatic parity on macOS.

---

## Development

### Prerequisites

- Python 3.12+
- Node.js 20+
- Git

```bash
git clone https://github.com/hydrahive/hydrahive2.0.git
cd hydrahive2.0

python3.12 -m venv .venv
source .venv/bin/activate
pip install -e core

cd frontend
npm ci
cd ..

./dev-start.sh
```

`dev-start.sh` supplies development secrets, starts the backend on `127.0.0.1:8001` and starts Vite.

### Verification

```bash
cd core
python -m pytest
python -m ruff check src tests

cd ../frontend
npx tsc --noEmit
npm run lint
npm run build
```

CI runs backend pytest + Ruff, a non-blocking dependency audit, frontend TypeScript and ESLint. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Configuration

Runtime settings use the `HH_` prefix. The Linux installer writes optional environment overrides to `/etc/hydrahive2/env` and creates secrets/PKI under `/etc/hydrahive2`.

| Variable | Code default | Purpose |
|---|---:|---|
| `HH_BASE_DIR` | `/opt/hydrahive2` | application source/build location |
| `HH_DATA_DIR` | `/var/lib/hydrahive2` | sessions database, agents, workspaces, modules, plugins and media data |
| `HH_CONFIG_DIR` | `/etc/hydrahive2` | users, provider/MCP configuration, secrets and compute PKI |
| `HH_SECRET_KEY` | **required** | JWT signing and credential-encryption root secret; installer generates it |
| `HH_JWT_EXPIRE_MINUTES` | `1440` | JWT lifetime |
| `HH_HOST` | `127.0.0.1` | backend bind address |
| `HH_PORT` | `8765` | code default; Linux installer configures `8001` behind nginx |
| `HH_CORS_ORIGINS` | localhost Vite origins | comma-separated browser origins |
| `HH_AGENTLINK_URL` | `http://127.0.0.1:9000` | local/remote AgentLink REST endpoint; explicit empty value disables it |
| `HH_AGENTLINK_TOKEN` | empty | optional AgentLink bearer token |
| `HH_PG_MIRROR_DSN` | empty | optional PostgreSQL data-mining mirror |
| `HH_MODULE_HUB_GIT_URL` | official module hub | primary module source |
| `HH_MODULE_HUB_GIT_URLS` | empty | additional comma-separated module hubs |
| `HH_ENABLE_DOCS` | false | expose Swagger at `/api/docs` and OpenAPI at `/api/openapi.json` |
| `HH_UPDATE_CHECK_ENABLED` | true | query the Git remote for update status |

Provider, mail, Matrix, Webmin, Samba, VM and compute features have additional settings. Prefer the UI credential/provider screens or `/etc/hydrahive2/env` over committing secrets.

---

## Security model

Verified implementation properties:

- new passwords use bcrypt; legacy SHA-256 hashes migrate after successful login;
- API access uses expiring JWTs or explicit API keys;
- newer principal-based resources resolve immutable user IDs and current roles;
- project routes enforce project membership/roles and record selected audit events;
- credential values are encrypted at rest with AES-GCM and stored with restrictive file mode;
- agents receive explicit tool/MCP/plugin selections and can require confirmation;
- the standard Linux edge uses HTTPS, security headers, request limits and compute-node mTLS;
- plugin manifests are validated and plugins are explicitly assigned to agents; plugin Python code runs in the backend process and must be trusted.

Important boundaries:

- some legacy APIs still use username/role dependencies and must enforce ownership themselves;
- authenticated data-mining queries are broader than strict per-user isolation;
- modules and plugins are trusted executable code, not security sandboxes;
- extension installation is privileged by design;
- the default TLS certificate is self-signed;
- cloud providers and external integrations receive the data needed for a chosen operation.

Read [SECURITY.md](SECURITY.md) and [docs/SECURITY_THREAT_MODEL.md](docs/SECURITY_THREAT_MODEL.md). Do not expose the development server directly to the public internet.

---

## Repository layout

```text
hydrahive2.0/
├── core/                    # FastAPI backend, runner, tools and persistence
├── frontend/                # React + TypeScript + Vite application
├── modules/                 # bundled Tasks/Patientenakte sources and example template
├── extensions/              # service manifests and install/Compose assets
├── node-agent/              # remote compute-node service
├── installer/               # install, update and migration scripts
├── mcp-servers/             # bundled MCP server helpers/examples
├── docs/                    # product, architecture, security and runbooks
├── SPEC.md                  # binding product baseline
└── CONTRIBUTING.md          # repository rules and checks
```

---

## Documentation

- [Feature inventory](docs/FEATURES.md) — implemented capabilities, module/extension catalogs and limitations
- [Release notes](docs/RELEASE_NOTES.md) — current unreleased changes and published-release pointer
- [User guide](docs/USER_GUIDE.md) — day-to-day workflows
- [Architecture](docs/ARCHITECTURE.md) — components, data flow and trust boundaries
- [Cockpits](docs/COCKPITS.md) — current navigation and workspace model
- [Documentation index](docs/README.md)
- [Installer guide](installer/README.md)
- [Frontend contributor guide](frontend/README.md)
- [Node-agent reference](node-agent/README.md)
- [Module hub](https://github.com/hydrahive/hydrahive2-modules)
- [Contributing](CONTRIBUTING.md)

---

## License and contribution

HydraHive is licensed under the [MIT License](LICENSE).

Bug reports and pull requests are welcome. Keep changes scoped, follow [CONTRIBUTING.md](CONTRIBUTING.md) and run the relevant verification commands before submitting a pull request.
