# HydraHive Linux installer

The installer provisions HydraHive on an apt-based Ubuntu/Debian host. The repository contains explicit upgrade handling for Ubuntu 24.04 and 26.04. Other releases must provide Python 3.12 and the required host capabilities; verify them before production use.

> The default component selection is broad: nginx, AgentLink, PostgreSQL, voice, Incus containers, libvirt VMs, Samba, WhatsApp and Tailscale are enabled unless declined. Use the interactive wizard or explicit `HH_INSTALL_*` values for a minimal host.

## Requirements

- root or `sudo` access;
- apt package management;
- outbound package/Git access;
- Python 3.12 availability (the script can add the deadsnakes PPA on Ubuntu when needed);
- Node.js 20+ (installed through NodeSource when needed);
- enough disk/RAM for selected components;
- hardware virtualization for VM support;
- Incus-compatible host for containers/voice;
- NVIDIA/CUDA-compatible hardware for automated local-media setup.

I cannot confirm from repository code alone that every Debian release works unchanged; the Python fallback uses an Ubuntu PPA. Test the target OS or provide Python 3.12 before installation.

## Quick start

```bash
git clone https://github.com/hydrahive/hydrahive2.0.git
cd hydrahive2.0
sudo bash installer/install.sh
```

If the clone is not already at `/opt/hydrahive2` and `HH_REPO_DIR` was not explicitly set, the installer moves the repository there and restarts itself.

### What the installer does

1. installs host dependencies, Node.js 20, Python 3.12, `uv/uvx`, GitHub CLI, ffmpeg and the `mmx` CLI;
2. creates the non-login `hydrahive` service account;
3. prepares `/var/lib/hydrahive2` and `/etc/hydrahive2`;
4. builds a Python virtual environment under `/opt/hydrahive2/.venv`;
5. installs the backend in editable mode and builds `frontend/dist`;
6. installs `llmfit` and, on compatible NVIDIA hosts, the local-media runtime;
7. provisions selected optional components;
8. writes and starts the `hydrahive2.service` systemd unit;
9. generates an application secret, compute CA and proxy secret;
10. configures nginx with a self-signed HTTPS certificate;
11. runs an optional LLM-provider setup wizard;
12. prints the login URL, generated administrator password and component summary.

The script is intended to be idempotent. Re-running it preserves stored wizard choices unless `--reconfigure` is supplied.

## Component wizard

Interactive runs ask about:

| Variable | Component | Default without a saved choice |
|---|---|---:|
| `HH_INSTALL_TAILSCALE` | Tailscale mesh VPN | `yes` |
| `HH_INSTALL_POSTGRES` | PostgreSQL data-mining mirror | `yes` |
| `HH_INSTALL_VOICE` | Wyoming Faster Whisper + Piper containers and optional mmx CLI | `yes` |
| `HH_INSTALL_CONTAINERS` | Incus container manager | `yes` |
| `HH_INSTALL_VMS` | QEMU/KVM, libvirt and websockify | `yes` |
| `HH_INSTALL_AGENTLINK` | HydraLink/AgentLink | `yes`; no interactive question, set `no` explicitly to skip |
| `HH_INSTALL_NGINX` | nginx HTTPS reverse proxy | `yes` |
| `HH_INSTALL_SAMBA` | project workspace shares | `yes` |
| `HH_INSTALL_WHATSAPP` | WhatsApp Node bridge dependencies | `yes` |

Voice requires the container manager; the installer turns containers back on when voice is selected.

Answers are stored at `/etc/hydrahive2/install.conf` with mode `0600`. Precedence is:

```text
explicit environment > saved install.conf > interactive answer > default
```

### Minimal/non-interactive example

```bash
sudo env \
  HH_INSTALL_TAILSCALE=no \
  HH_INSTALL_POSTGRES=no \
  HH_INSTALL_VOICE=no \
  HH_INSTALL_CONTAINERS=no \
  HH_INSTALL_VMS=no \
  HH_INSTALL_AGENTLINK=no \
  HH_INSTALL_SAMBA=no \
  HH_INSTALL_WHATSAPP=no \
  HH_INSTALL_NGINX=yes \
  bash installer/install.sh --no-prompt
```

Skipping AgentLink removes agent-to-agent delegation. Skipping nginx also removes the default HTTPS/static-file edge and requires a separately configured reverse proxy or direct development-style access.

### Reconfigure

```bash
sudo bash /opt/hydrahive2/installer/install.sh --reconfigure
```

This asks the component questions again. An explicit environment value still wins.

## Core settings

| Variable | Installer default | Meaning |
|---|---:|---|
| `HH_REPO_DIR` | `/opt/hydrahive2` | repository/runtime code path |
| `HH_USER` | `hydrahive` | systemd service account |
| `HH_DATA_DIR` | `/var/lib/hydrahive2` | database, agents, workspaces, modules, media and runtime data |
| `HH_CONFIG_DIR` | `/etc/hydrahive2` | users/API keys, provider/MCP config, application secret, environment overrides, TLS and compute PKI |
| `HH_HOST` | `127.0.0.1` | uvicorn bind address |
| `HH_PORT` | `8001` | uvicorn port behind nginx |
| `HH_TAILSCALE_AUTHKEY` | empty | optional Tailscale enrollment key |

Keep `HH_HOST` on loopback in the standard installation. The compute-agent proxy setup explicitly rejects a non-loopback backend host because trusted proxy headers must not be accepted from arbitrary network clients.

Additional application/provider environment values belong in:

```text
/etc/hydrahive2/env
```

The file is read by systemd and owned `root:hydrahive` with restricted permissions. Restart HydraHive after changes:

```bash
sudo systemctl restart hydrahive2
```

## First login

The installer prints:

```text
URL:       https://<server-ip>
Benutzer:  admin
Passwort:  <generated value>
```

The initial password is also captured temporarily by the installer from `/etc/hydrahive2/.admin_initial_password` or the current boot journal. Change it after the first login.

The nginx certificate is self-signed and includes loopback plus the detected server IP as subject alternative names. A browser warning is therefore expected until the certificate is explicitly trusted or replaced.

## Files and services

### Main paths

```text
/opt/hydrahive2/                         code and virtual environment
/var/lib/hydrahive2/                     persistent HH_DATA_DIR
/etc/hydrahive2/                         secrets, env, TLS and compute PKI
/etc/nginx/sites-available/hydrahive2    generated nginx config
/etc/systemd/system/hydrahive2.service   backend service
/var/log/hydrahive2-update.log           update log
/var/log/hydrahive2-voice.log            voice setup log
/var/log/hydrahive2-bridge.log           bridge setup log
/var/log/hydrahive2-samba.log            Samba setup log
/var/log/hydrahive2-migration.log        migration log
```

### Main commands

```bash
sudo systemctl status hydrahive2
sudo systemctl restart hydrahive2
sudo systemctl stop hydrahive2
sudo journalctl -u hydrahive2 -f

sudo nginx -t
sudo systemctl status nginx
```

Systemd timers poll for UI-created update, restart, voice, bridge, Samba and migration request files.

## nginx behavior

The generated nginx configuration:

- redirects HTTP to HTTPS, except health-data ingestion;
- serves `frontend/dist`;
- proxies `/api/` and WebSocket upgrades to `127.0.0.1:8001` by default;
- gives chat messages an approximately 205 MiB request limit;
- permits larger API uploads for VM ISO/media workflows;
- proxies VNC and AgentLink;
- adds CSP, HSTS and other security headers;
- requires mTLS for the compute-agent connect endpoint.

After editing the generated configuration:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Re-running the installer can overwrite generated configuration, so persistent customizations should be documented and reapplied deliberately.

## Updates

```bash
cd /opt/hydrahive2
sudo bash installer/update.sh
```

The updater performs repository/dependency/frontend work and restarts the service. It has rollback handling, but create a backup before major updates because schema and external-service changes cannot always be undone only by changing Git commits.

The UI can also create an update request that is consumed by `hydrahive2-update.timer`/`.service`.

## Backup and migration

Back up at minimum:

```text
/var/lib/hydrahive2
/etc/hydrahive2
```

Also back up external mount data, PostgreSQL, Docker volumes and third-party extension data separately. They are not guaranteed to be inside `HH_DATA_DIR`.

Server-to-server migration is implemented by `installer/migrate.sh` and a dedicated no-timeout systemd service. Review source, target, SSH access and disk capacity before starting a large transfer.

## Security notes

The systemd service uses:

- a dedicated non-login service user;
- `PrivateTmp=true`;
- `ProtectHome=read-only`;
- explicit writable paths;
- a generated JWT/credential-encryption root secret;
- a loopback backend by default.

It intentionally does **not** enable `NoNewPrivileges` or `ProtectSystem=strict`, because service-extension installation needs privileged operations. The installer writes sudo rules that allow the service account to invoke shell/Docker/sysctl commands for extension management. Consequently:

- extension APIs must remain administrator-only;
- an administrator or extension script is a host-level trust boundary;
- installed manifests/scripts must be reviewed;
- the admin interface should not be publicly exposed without additional controls.

See [../SECURITY.md](../SECURITY.md) and [../docs/SECURITY_THREAT_MODEL.md](../docs/SECURITY_THREAT_MODEL.md).

## Troubleshooting

### Backend does not start

```bash
sudo systemctl status hydrahive2 --no-pager
sudo journalctl -u hydrahive2 -n 150 --no-pager
```

Check `/etc/hydrahive2/env`, ownership of `HH_DATA_DIR`, Python dependency errors and free disk space.

### nginx returns 502

```bash
sudo nginx -t
sudo systemctl status nginx hydrahive2 --no-pager
curl -fsS http://127.0.0.1:8001/api/health
```

If the final command fails, diagnose the backend first. If it succeeds, inspect nginx logs/configuration.

### Frontend is blank or assets return 404

```bash
cd /opt/hydrahive2/frontend
sudo -u hydrahive npm install --no-fund --no-audit
sudo -u hydrahive npm run build
sudo systemctl reload nginx
```

Do not hard-cache `index.html`; the generated nginx configuration intentionally revalidates HTML while caching content-hashed assets.

### `uvx` is missing

Re-run the dependency phase or install `uv` and copy `uv`/`uvx` into a path visible to the service. The normal installer installs both under `/usr/local/bin` when bootstrapping from root.

### AgentLink failed

The main installation continues but reports a prominent failure. Retry:

```bash
sudo bash /opt/hydrahive2/installer/modules/75-agentlink.sh
```

Until it succeeds, `ask_agent`/delegation is unavailable.

### Voice install failed

Check Incus and the dedicated log:

```bash
incus list
sudo tail -n 200 /var/log/hydrahive2-voice.log
```

The voice stack depends on container support and can take substantially longer than the base installation.
