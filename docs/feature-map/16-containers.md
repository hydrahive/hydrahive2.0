# Containers

Das **Containers**-Subsystem managt LXC-Container über **incus** (CLI-Subprocess)
direkt aus HydraHive2 heraus. Es ist die "Schwester von VMs" — selber Daten-/
State-Aufbau (desired_state vs actual_state, Reconciler, Per-User-Owner, br0-
Bridge), aber leichter als VMs (kein QEMU/KVM, schneller Boot) und enger als
Docker (kein Layer-FS). Zielanwendung laut SPEC: kleine Dauer-Dienste wie SearXNG,
Linkding, Vaultwarden, eigene Tools (`SPEC.md:561-595`).

---

## WAS

### Backend — Datenmodell / Typen (`containers/models.py`)
- `Container` (dataclass) — Container-Datensatz mit allen DB-Feldern (`containers/models.py:12-28`).
- `ContainerImage` (dataclass) — Image-Katalog-Eintrag (alias, fingerprint, description, architecture, size_bytes); **nur definiert, nirgends benutzt** (`containers/models.py:31-37`).
- `DesiredState` = `"running" | "stopped"` (Literal, `containers/models.py:7`).
- `ActualState` = `"created" | "starting" | "running" | "stopping" | "stopped" | "error"` (Literal, `containers/models.py:8`).
- `NetworkMode` = `"bridged" | "isolated"` (Literal, `containers/models.py:9`).
- `NAME_RE` — Name-Allowlist-Regex `^[a-zA-Z][a-zA-Z0-9-]{0,62}$` (max 63 Zeichen wie incus, `containers/models.py:41`).
- `IMAGE_RE` — Image-Allowlist-Regex `^(?:[a-zA-Z0-9][a-zA-Z0-9-]*:)?[a-zA-Z0-9][a-zA-Z0-9._/-]*$` (optionaler `<remote>:`-Präfix, Issue #185 — Flag-Injection-Härtung, `containers/models.py:45`).
- `MIN_CPU=1`, `MAX_CPU=16` (`containers/models.py:46-47`).
- `MIN_RAM_MB=64`, `MAX_RAM_MB=32768` (`containers/models.py:48-49`).
- `QUICK_IMAGES` — kuratierte Quick-Pick-Liste fürs UI: `debian/12`, `debian/13`, `ubuntu/24.04`, `ubuntu/22.04`, `alpine/3.21`, `archlinux`, `centos/9-Stream` (`containers/models.py:52-60`).

### Backend — DB-CRUD (`containers/db.py`)
- `_row_to_container(r)` — sqlite3.Row → `Container`, deserialisiert `last_error_params` aus JSON, behandelt `project_id` defensiv (nur wenn Spalte da, `containers/db.py:12-23`).
- `create(owner, name, image, network_mode, cpu, ram_mb, description)` — INSERT, `uuid7()` als ID, `desired_state='stopped'`, `actual_state='created'`, gibt frischen `get()` zurück (`containers/db.py:26-39`).
- `get(container_id)` — SELECT by PK, `Container | None` (`containers/db.py:42-47`).
- `list_(owner=None)` — alle Container (owner=None → admin/global) oder eines Owners, `ORDER BY created_at DESC` (`containers/db.py:50-61`).
- `name_taken(name, exclude_id=None)` — Existenz-Check über `name` (global eindeutig), optional eigene ID ausgeschlossen (`containers/db.py:64-75`).
- `update_state(container_id, *, desired, actual, error_code=..., error_params=...)` — partielles State-Update; Sentinel `...` = "nicht ändern", `None` = explizit löschen; serialisiert error_params zu JSON; updated_at immer (`containers/db.py:78-94`).
- `delete(container_id)` — DELETE by PK (`containers/db.py:97-99`).
- `update_container_config(container_id, *, name, description=..., cpu=..., ram_mb=...)` — Config-Update (Name/Desc/CPU/RAM); cpu/ram_mb können explizit auf `None` = "unbegrenzt" (`containers/db.py:102-119`).
- `set_project(container_id, project_id|None)` — Projekt-Zuweisung (`containers/db.py:122-127`).
- `list_for_project(project_id)` — Container eines Projekts (`containers/db.py:130-136`).
- `clear_project_assignments(project_id)` — setzt `project_id=NULL` für alle eines Projekts (beim Projekt-Löschen, `containers/db.py:139-143`).

### Backend — incus-CLI-Wrapper (`containers/incus_client.py`)
- `IncusError(code, **params)` — strukturierte Fehlerklasse mit `.code` + `.params` (`containers/incus_client.py:21-25`).
- `is_available()` — `shutil.which("incus") is not None` (`containers/incus_client.py:28-29`).
- `_run(*args, timeout=60, input_bytes=None)` — async Subprocess-Runner; returnt `(rc, stdout, stderr)`; wirft `incus_missing` wenn binary fehlt, `incus_timeout` bei Timeout (kill + raise, `containers/incus_client.py:32-52`).
- `launch(name, image, *, network_mode, cpu, ram_mb, bridge="br0", privileged=True)` — erzeugt+startet Container; baut `-c limits.cpu/memory`-Opts, bei privileged `security.privileged=true` + `security.nesting=true`, `--`-Separator vor Positional-Args; danach Network-Device-Setup (`containers/incus_client.py:55-100`).
- `stop(name, *, force=False)` — `incus stop [--force]`; toleriert "is not running" (`containers/incus_client.py:103-109`).
- `start(name)` — `incus start`; toleriert "already running" (`containers/incus_client.py:112-115`).
- `restart_(name)` — `incus restart` (`containers/incus_client.py:118-121`).
- `delete(name, *, force=True)` — `incus delete [--force]`; toleriert "not found" (`containers/incus_client.py:124-130`).
- Re-Export am Datei-Ende: `info, list_running_names, show_log, show_config, list_images` aus `_incus_inspect` (`containers/incus_client.py:133-135`).

### Backend — Read-only incus-Inspektion (`containers/_incus_inspect.py`)
- `info(name)` — voller Status-Block via `incus query /1.0/instances/<name>?recursion=1`, JSON → dict|None (`containers/_incus_inspect.py:9-17`).
- `list_running_names()` — `incus list --format=json --columns=ns`, returnt `set[str]` der laufenden Namen (`containers/_incus_inspect.py:20-28`).
- `show_log(name)` — `incus info <name> --show-log` (Lifecycle-Log als Text, `containers/_incus_inspect.py:31-36`).
- `show_config(name)` — `incus config show <name>` (YAML-Config als Text, `containers/_incus_inspect.py:39-44`).
- `list_images(remote="images")` — `incus image list <remote>: --format=json` (Image-Katalog); **definiert, aber nirgends aufgerufen** (`containers/_incus_inspect.py:47-55`).

### Backend — Lifecycle-Orchestrierung (`containers/lifecycle.py`)
- `_bridge()` — `settings.vms_bridge` (br0, gemeinsam mit VMs, `containers/lifecycle.py:13-14`).
- `create_and_start(container_id)` — setzt desired=running/actual=starting, ruft `incus.launch`, bei Erfolg actual=running, bei `IncusError` actual=error + error_code/params + re-raise (`containers/lifecycle.py:17-34`).
- `start(container_id)` — desired=running/actual=starting → `incus.start` → running (oder error, `containers/lifecycle.py:37-49`).
- `stop(container_id, *, force=False)` — desired=stopped/actual=stopping → `incus.stop` → stopped (oder error, `containers/lifecycle.py:52-63`).
- `restart_(container_id)` — `incus.restart_` → actual=running, error gecleared; **setzt KEIN starting/stopping zwischendrin** (`containers/lifecycle.py:66-72`).
- `delete(container_id)` — `incus.delete(force=True)`; schluckt IncusError ("incus weg, aber DB sauber halten") und löscht DB-Zeile in jedem Fall (`containers/lifecycle.py:75-84`).

### Backend — PTY-Console-Bridge (`containers/console.py`)
- `ConsoleSession(name)` — Lifecycle einer PTY-Session (`containers/console.py:21-24`).
- `ConsoleSession.start(on_output, on_exit)` — öffnet PTY-Paar, setzt Default-Größe 24×80, startet `incus exec <name> --mode=interactive -- bash` mit Slave als stdin/stdout/stderr, registriert `add_reader` auf Master-FD, Exit-Watcher-Task (`containers/console.py:32-54`).
- `ConsoleSession._on_master_readable()` — liest 4096 Bytes vom Master-FD, ruft `on_output`-Callback; cleanup bei OSError/EOF (`containers/console.py:56-68`).
- `ConsoleSession._cleanup_reader()` — `remove_reader` (`containers/console.py:70-75`).
- `ConsoleSession._watch_exit()` — wartet auf Prozess-Exit, ruft `on_exit` (`containers/console.py:77-85`).
- `ConsoleSession.write(data)` — `os.write` an Master-FD (`containers/console.py:87-93`).
- `ConsoleSession.resize(rows, cols)` — `TIOCSWINSZ` ioctl (`containers/console.py:95-104`).
- `ConsoleSession.stop()` — cleanup reader, terminate→(3s)→kill Prozess, schließt Master-FD (`containers/console.py:106-124`).

### Backend — Reconciler (`containers/reconciler.py`)
- `POLL_INTERVAL_S = 4.0` (`containers/reconciler.py:12`).
- `ACTIVE_STATES = ("running", "starting", "stopping")` (`containers/reconciler.py:13`).
- `reconcile_once()` — holt `incus.list_running_names()` + alle DB-Container, gleicht ab: laufend+nicht-running → running; nicht-laufend+desired=running → error (`container_not_running`); nicht-laufend+desired=stopped → stopped (`containers/reconciler.py:16-39`).
- `run_loop(stop)` — Endlosschleife mit `wait_for(stop.wait(), 4s)` (`containers/reconciler.py:42-50`).

### Backend — Routes-Aggregator (`api/routes/containers.py`)
- `router` — bündelt CRUD- + Ops-Sub-Router, damit `api/main.py` einen Include-Call braucht (`api/routes/containers.py:13-15`).

### Backend — Route-Helpers (`api/routes/_container_helpers.py`)
- `ContainerCreate` (Pydantic) — name (1-63), description (≤500), image (1-120), cpu (1-16|None), ram_mb (64-32768|None), network_mode (default "bridged", `api/routes/_container_helpers.py:11-17`).
- `ContainerUpdate` (Pydantic) — name|None, description|None, cpu|None, ram_mb|None, `clear_cpu` bool, `clear_ram` bool (`api/routes/_container_helpers.py:20-26`).
- `is_admin(role)` — `role == "admin"` (`api/routes/_container_helpers.py:29-30`).
- `container_or_404(container_id, owner, role)` — lädt Container; 404 wenn nicht da, 403 wenn nicht Owner und nicht Admin (`api/routes/_container_helpers.py:33-39`).

### Backend — CRUD-Routen (`api/routes/containers_crud.py`, prefix `/api/containers`)
- `GET /api/containers` — `list_containers`, Admin sieht alle, sonst nur eigene; gibt `asdict()`-Liste (`api/routes/containers_crud.py:25-29`).
- `GET /api/containers/quick-images` — `quick_images`, returnt `QUICK_IMAGES`-Liste (`api/routes/containers_crud.py:32-34`).
- `POST /api/containers` (201) — `create_container`: validiert NAME_RE, network_mode, IMAGE_RE; setzt `images:`-Präfix wenn kein `:`; name_taken-Check; incus.is_available-Check; DB-create; `lifecycle.create_and_start`; bei IncusError → DB-Zeile löschen + 500 mit Code (`api/routes/containers_crud.py:37-68`).
- `GET /api/containers/{id}` — `get_container`, via container_or_404 (`api/routes/containers_crud.py:71-76`).
- `PATCH /api/containers/{id}` — `update_container`: nur wenn actual_state in (stopped/created/error), sonst 400 `container_must_be_stopped`; Name-Re + name_taken-Validierung; `update_container_config` mit Sentinel-Logik für cpu/ram (clear_* → None) (`api/routes/containers_crud.py:79-100`).
- `DELETE /api/containers/{id}` (204) — `delete_container`, container_or_404 → `lifecycle.delete` (`api/routes/containers_crud.py:103-109`).

### Backend — Ops/Inspektions-Routen (`api/routes/containers_ops.py`, prefix `/api/containers`)
- `POST /api/containers/{id}/start` — `start_container` → lifecycle.start; IncusError → 400 mit Code (`api/routes/containers_ops.py:22-32`).
- `POST /api/containers/{id}/stop` — `stop_container` → lifecycle.stop(force=False) (`api/routes/containers_ops.py:35-45`).
- `POST /api/containers/{id}/restart` — `restart_container` → lifecycle.restart_ (`api/routes/containers_ops.py:48-58`).
- `GET /api/containers/{id}/log` — `container_log` → `{"text": incus.show_log(name)}` (`api/routes/containers_ops.py:61-67`).
- `GET /api/containers/{id}/config` — `container_config` → `{"text": incus.show_config(name)}` (`api/routes/containers_ops.py:70-76`).
- `GET /api/containers/{id}/info` — `container_info`: Live-Info via `incus.info`; extrahiert status, IPv4 (eth0/inet/global), cpu_usage_ns, memory_bytes, memory_peak_bytes; `{"alive": False}` wenn info None (`api/routes/containers_ops.py:79-102`).

### Backend — WebSocket-Console (`api/routes/container_console.py`)
- `_authenticate(token)` — JWT via `_decode`, returnt `(sub, role)` oder None; fängt `(ValueError, KeyError, jwt.InvalidTokenError)` (`api/routes/container_console.py:27-34`).
- `WS /api/containers/{id}/console?token=...` — `container_console`: Auth via Query-Param (Browser-WS kann keinen Auth-Header); Close-Codes 4401 (unauth), 4404 (not found / kein Zugriff), 4409 (nicht running), 4500 (Backend/RuntimeError); akzeptiert, startet `ConsoleSession`, routet input/resize-Frames (JSON-Text) → PTY, PTY-Bytes → binary-Frames; finally → `session.stop()` (`api/routes/container_console.py:37-100`).

### Frontend — API-Client (`frontend/src/features/containers/api.ts`)
- `containersApi.list()`, `.get(id)`, `.info(id)`, `.create(input)`, `.update(id, patch)`, `.remove(id)`, `.start(id)`, `.stop(id)`, `.restart(id)`, `.quickImages()`, `.log(id)`, `.config(id)` — je ein Wrapper auf den entsprechenden Endpoint (`frontend/src/features/containers/api.ts:4-24`).

### Frontend — Typen (`frontend/src/features/containers/types.ts`)
- `DesiredState`, `ActualState`, `NetworkMode` — spiegeln Backend-Literals (`types.ts:1-3`).
- `Container` interface — alle DB-Felder (ohne `project_id` im FE-Typ!) (`types.ts:5-20`).
- `ContainerInfo` interface — alive/status/ipv4/cpu_usage_ns/memory_bytes/memory_peak_bytes (`types.ts:22-29`).
- `ContainerCreateInput` interface — name/description/image/cpu/ram_mb/network_mode (`types.ts:31-38`).

### Frontend — Seiten / Komponenten
- `ContainersPage` — Übersichtsseite: Header, Refresh-Button, "Neuer Container"-Button, Summary-Cards (total/running), 4s-Polling, Grid aus `ContainerCard`, Empty-State, Create/Edit-Dialoge (`frontend/src/features/containers/ContainersPage.tsx:14-102`).
- `SummaryCard` — Kennzahl-Karte (`ContainersPage.tsx:104-111`).
- `ContainerCard` — Karten-View pro Container: Name-Link zur Detail-Page, Description, Image, StatusBadge, Spec-Chips (CPU/RAM/Network/IP), Live-RAM-Bar (4s-Polling via `info`), Error-Code-Anzeige, Action-Buttons (Start/Console/Restart/Stop), Edit/Delete (`ContainerCard.tsx:21-139`).
- `Spec` — Chip-Subkomponente (`ContainerCard.tsx:141-151`).
- `ContainerDetailPage` — Detail-View mit 4 Tabs (Console/Logs/Stats/Config), 5s-Polling für Container-State, Back-Button, Konsole-Tab nur wenn running (`ContainerDetailPage.tsx:17-105`).
- `BackLink`, `TabBtn` — Detail-Page-Hilfskomponenten (`ContainerDetailPage.tsx:107-130`).
- `CreateContainerDialog` — Modal: Name/Desc/Image (Quick-Pick-Grid vs. Custom-Toggle)/CPU/RAM/Network-Radio; Live-Name-Validierung; lädt quick-images (`CreateContainerDialog.tsx:15-137`).
- `EditContainerDialog` — Modal: Name/Desc editierbar, Image read-only; CPU/RAM mit Checkbox (gesetzt vs. unbegrenzt); nur editierbar wenn stopped/created/error; Dirty-Tracking; baut Partial-Patch (`EditContainerDialog.tsx:15-135`).
- `Field`, `RadioCard` — Dialog-Hilfskomponenten (`_containerDialogHelpers.tsx:1-23`).
- `Field` (lokal in EditDialog) — eigene Variante (`EditContainerDialog.tsx:137-144`).
- `ConsolePane` — xterm.js-Terminal + FitAddon, WebSocket-Verbindung mit Token-Query, resize/input-Frames, Status-Anzeige (connecting/connected/closed), Close-Code-Mapping zu lokalisierten Fehlern (`ConsolePane.tsx:15-104`).
- `ContainerConsoleModal` — Modal-Wrapper um `ConsolePane` (für Console-Button auf der Karte, `ContainerConsoleModal.tsx:12-29`).
- `ContainerLogPane` — Lifecycle-Log-Viewer (`incus info --show-log`), Auto-Refresh-Checkbox (5s), manueller Refresh (`ContainerLogPane.tsx:10-60`).
- `ContainerStatsPane` — Live-Stats (RAM-Bar+Peak, CPU-Sekunden, Netzwerk/IP), 3s-Polling, nur wenn running (`ContainerStatsPane.tsx:13-95`).
- `ContainerConfigPane` — `incus config show`-Viewer, manueller Refresh (`ContainerConfigPane.tsx:9-44`).
- `ContainerStatusBadge` — Status-Pille mit Farb-Preset + Pulse-Animation (starting/stopping), lokalisiertem Label (`StatusBadge.tsx:13-22`).
- `PRESETS` — Status→CSS+pulse-Map (`StatusBadge.tsx:4-11`).

### Routing / i18n / Navigation
- Route `/containers` → `ContainersPage`, `/containers/:id` → `ContainerDetailPage` (`frontend/src/App.tsx:76-77`).
- i18n-Namespace `containers` (de+en) registriert (`frontend/src/i18n/index.ts:28,61,79,90,108`).
- Sidebar-Item `/containers`, Icon `Box`, group `infrastructure` (`frontend/src/shared/nav-config.ts:46`).
- Farb-Zuordnung `/containers → "sky"` (`frontend/src/shared/colors.ts:23`).

---

## WIE

### Container-Erstellung (Klick → Container läuft)
1. User klickt "Neuer Container" → `CreateContainerDialog` öffnet, lädt `quickImages()` (`CreateContainerDialog.tsx:28-30`).
2. User wählt Image (Quick-Pick oder Custom), Name, optional Desc/CPU/RAM/Network.
3. Client-seitige Name-Validierung (`/^[a-zA-Z][a-zA-Z0-9-]{0,62}$/`, `CreateContainerDialog.tsx:32`).
4. `submit` → `containersApi.create()` → `POST /api/containers`.
5. Backend (`create_container`, `containers_crud.py:37-68`):
   - NAME_RE, network_mode, IMAGE_RE prüfen (alle 400 mit jeweiligem Code).
   - Image normalisieren: `images:`-Präfix nur wenn kein `:` enthalten.
   - `name_taken` → 409.
   - `incus.is_available` → 503 `incus_missing`.
   - DB-Zeile via `cdb.create` (actual=created, desired=stopped).
   - `lifecycle.create_and_start(id)`:
     - DB → desired=running/actual=starting.
     - `incus.launch`: `incus launch <opts> -- <image> <name>` (300s Timeout) → bei bridged: `config device override eth0 parent=br0 nictype=bridged` (Fallback: `config device add`) + `restart`; bei isolated: `config device remove eth0`.
     - DB → actual=running.
   - **Bei IncusError im launch**: actual=error + error_code/params gespeichert, raise → CRUD-Route fängt es, **löscht die DB-Zeile wieder** und gibt 500 mit Code zurück (`containers_crud.py:65-67`). Kein Waisen-Datensatz.
6. Dialog `onCreated()` → `refresh()` der Liste.

### State-Maschine (desired_state × actual_state)
- `created` (Default nach DB-Insert) → `starting` → `running` | `error`.
- `running` → (stop) `stopping` → `stopped` | `error`.
- `running` → (restart_) → `running` direkt (kein Zwischen-State).
- Reconciler korrigiert Drift: actual ∈ ACTIVE_STATES (running/starting/stopping) wird alle 4s gegen `incus list` abgeglichen (`reconciler.py:26-39`):
  - laufend, aber DB≠running → running.
  - nicht laufend, desired=running → **error** + `container_not_running`.
  - nicht laufend, desired=stopped → stopped.
  - **`error`, `stopped`, `created` werden vom Reconciler NICHT angefasst** (nicht in ACTIVE_STATES) — bleiben "sticky" bis ein expliziter Lifecycle-Call sie ändert.

### Console (Klick "Console" → interaktive Shell)
1. Karte/Detail-Tab → `ConsolePane` mountet, holt `token` aus `useAuthStore` (`ConsolePane.tsx:23`).
2. xterm.js-`Terminal` + `FitAddon` → `term.open` → `fit.fit()`.
3. WebSocket-URL: `${ws|wss}://host/api/containers/<id>/console?token=<jwt>` (`ConsolePane.tsx:42-44`).
4. `ws.onopen` → resize-Frame mit term.rows/cols senden.
5. Backend (`container_console`, `container_console.py:37-100`):
   - `_authenticate(token)` → None → close 4401.
   - `cdb.get` → nicht da / kein Zugriff → close 4404.
   - actual_state≠running → close 4409.
   - `ws.accept()`, `ConsoleSession(name).start(on_output, on_exit)`:
     - PTY-Paar, Default 24×80, `incus exec <name> --mode=interactive -- bash` (Slave als stdio), `add_reader` auf Master.
     - PTY-Output → `on_output(data)` → `ws.send_bytes(data)` (binary).
   - Empfangs-Loop: Text-Frame → JSON parse → `input` → `session.write(data.encode)`, `resize` → `session.resize(rows, cols)`; Binary-Frame → `session.write(bytes)`.
   - `WebSocketDisconnect` → break; finally → `session.stop()` (terminate→kill, FD close).
6. Client: `ws.onmessage` (ArrayBuffer) → `term.write`; `term.onData` → input-Frame; `ResizeObserver`/`window.resize` → fit + resize-Frame; `ws.onclose` → Close-Code → lokalisierte Fehlermeldung.

### Live-Info-Polling
- `ContainerCard` (4s), `ContainerStatsPane` (3s), `ContainerDetailPage` (5s State-Reload), `ContainersPage` (4s Liste) — alle setInterval mit `alive`-Guard + cleanup.
- `info`-Endpoint parst incus' `state.network.eth0.addresses` (nur `family=inet`, `scope=global`), `state.cpu.usage`, `state.memory.usage`/`usage_peak`.

### Projekt-Zuweisung (Cross-Subsystem)
- `projects_servers.py:34` → `list_for_project` zeigt zugewiesene Container.
- `projects_servers.py:83` → `set_project(id, project_id)` beim Zuweisen.
- `projects_servers.py:111` → `set_project(id, None)` beim Entfernen.
- `projects/config.py:121` → `clear_project_assignments` beim Projekt-Löschen (kein CASCADE der Container selbst — die gehören dem User).
- `dashboard.py:42-82` → Container fließen in Dashboard-Kennzahlen (running-Count, Server-Liste, servers_total).

### Startup/Shutdown
- `api/lifespan.py:132-134`: `container_reconciler.run_loop` als Task gestartet.
- `api/lifespan.py:221`: `container_reconciler_stop.set()` beim Shutdown, dann `wait_for(task, 5s)` (`lifespan.py:225-...`).
- Router-Registrierung: `api/main.py:129` (containers_router), `api/main.py:139` (container_console_router).

---

## WO

### Backend-Module
- `core/src/hydrahive/containers/__init__.py` — leer.
- `core/src/hydrahive/containers/models.py:12` — `Container` dataclass.
- `core/src/hydrahive/containers/models.py:31` — `ContainerImage` dataclass (ungenutzt).
- `core/src/hydrahive/containers/models.py:41-60` — NAME_RE/IMAGE_RE/Limits/QUICK_IMAGES.
- `core/src/hydrahive/containers/db.py:12` — `_row_to_container`.
- `core/src/hydrahive/containers/db.py:26` — `create`.
- `core/src/hydrahive/containers/db.py:42` — `get`.
- `core/src/hydrahive/containers/db.py:50` — `list_`.
- `core/src/hydrahive/containers/db.py:64` — `name_taken`.
- `core/src/hydrahive/containers/db.py:78` — `update_state`.
- `core/src/hydrahive/containers/db.py:97` — `delete`.
- `core/src/hydrahive/containers/db.py:102` — `update_container_config`.
- `core/src/hydrahive/containers/db.py:122` — `set_project`.
- `core/src/hydrahive/containers/db.py:130` — `list_for_project`.
- `core/src/hydrahive/containers/db.py:139` — `clear_project_assignments`.
- `core/src/hydrahive/containers/incus_client.py:21` — `IncusError`.
- `core/src/hydrahive/containers/incus_client.py:28` — `is_available`.
- `core/src/hydrahive/containers/incus_client.py:32` — `_run`.
- `core/src/hydrahive/containers/incus_client.py:55` — `launch`.
- `core/src/hydrahive/containers/incus_client.py:103` — `stop`.
- `core/src/hydrahive/containers/incus_client.py:112` — `start`.
- `core/src/hydrahive/containers/incus_client.py:118` — `restart_`.
- `core/src/hydrahive/containers/incus_client.py:124` — `delete`.
- `core/src/hydrahive/containers/incus_client.py:133-135` — Re-Export von `_incus_inspect`.
- `core/src/hydrahive/containers/_incus_inspect.py:9` — `info`.
- `core/src/hydrahive/containers/_incus_inspect.py:20` — `list_running_names`.
- `core/src/hydrahive/containers/_incus_inspect.py:31` — `show_log`.
- `core/src/hydrahive/containers/_incus_inspect.py:39` — `show_config`.
- `core/src/hydrahive/containers/_incus_inspect.py:47` — `list_images` (ungenutzt).
- `core/src/hydrahive/containers/lifecycle.py:17` — `create_and_start`.
- `core/src/hydrahive/containers/lifecycle.py:37` — `start`.
- `core/src/hydrahive/containers/lifecycle.py:52` — `stop`.
- `core/src/hydrahive/containers/lifecycle.py:66` — `restart_`.
- `core/src/hydrahive/containers/lifecycle.py:75` — `delete`.
- `core/src/hydrahive/containers/console.py:21` — `ConsoleSession`.
- `core/src/hydrahive/containers/console.py:32` — `.start`.
- `core/src/hydrahive/containers/console.py:87` — `.write`.
- `core/src/hydrahive/containers/console.py:95` — `.resize`.
- `core/src/hydrahive/containers/console.py:106` — `.stop`.
- `core/src/hydrahive/containers/reconciler.py:16` — `reconcile_once`.
- `core/src/hydrahive/containers/reconciler.py:42` — `run_loop`.

### API-Routen
- `core/src/hydrahive/api/routes/containers.py:13-15` — Aggregator.
- `core/src/hydrahive/api/routes/containers_crud.py:25` — `GET /api/containers`.
- `core/src/hydrahive/api/routes/containers_crud.py:32` — `GET /api/containers/quick-images`.
- `core/src/hydrahive/api/routes/containers_crud.py:37` — `POST /api/containers`.
- `core/src/hydrahive/api/routes/containers_crud.py:71` — `GET /api/containers/{id}`.
- `core/src/hydrahive/api/routes/containers_crud.py:79` — `PATCH /api/containers/{id}`.
- `core/src/hydrahive/api/routes/containers_crud.py:103` — `DELETE /api/containers/{id}`.
- `core/src/hydrahive/api/routes/containers_ops.py:22` — `POST .../start`.
- `core/src/hydrahive/api/routes/containers_ops.py:35` — `POST .../stop`.
- `core/src/hydrahive/api/routes/containers_ops.py:48` — `POST .../restart`.
- `core/src/hydrahive/api/routes/containers_ops.py:61` — `GET .../log`.
- `core/src/hydrahive/api/routes/containers_ops.py:70` — `GET .../config`.
- `core/src/hydrahive/api/routes/containers_ops.py:79` — `GET .../info`.
- `core/src/hydrahive/api/routes/container_console.py:27` — `_authenticate`.
- `core/src/hydrahive/api/routes/container_console.py:37` — `WS .../console`.
- `core/src/hydrahive/api/routes/_container_helpers.py:11` — `ContainerCreate`.
- `core/src/hydrahive/api/routes/_container_helpers.py:20` — `ContainerUpdate`.
- `core/src/hydrahive/api/routes/_container_helpers.py:29` — `is_admin`.
- `core/src/hydrahive/api/routes/_container_helpers.py:33` — `container_or_404`.
- `core/src/hydrahive/api/routes/_server_route_helpers.py:38` — `container_dict` (Projekt-Server-Liste).

### Wiring / Cross-Module
- `core/src/hydrahive/api/main.py:26-27` — Router-Imports.
- `core/src/hydrahive/api/main.py:129` — include containers_router.
- `core/src/hydrahive/api/main.py:139` — include container_console_router.
- `core/src/hydrahive/api/lifespan.py:29` — Reconciler-Import.
- `core/src/hydrahive/api/lifespan.py:132-134` — Reconciler-Task-Start.
- `core/src/hydrahive/api/lifespan.py:221,225` — Reconciler-Shutdown.
- `core/src/hydrahive/api/routes/projects_servers.py:34,83,111` — Projekt-Zuweisung.
- `core/src/hydrahive/projects/config.py:114,121` — clear bei Projekt-Löschung.
- `core/src/hydrahive/api/routes/dashboard.py:42-82` — Dashboard-Aggregation.
- `core/src/hydrahive/settings/_infra.py:54` — `vms_bridge` (`HH_VMS_BRIDGE`, Default br0).
- `core/src/hydrahive/api/middleware/auth.py:27` — `_decode` (vom WS-Auth genutzt).
- `core/src/hydrahive/api/middleware/errors.py:21` — `coded` (alle API-Fehler).

### DB-Migrationen
- `core/src/hydrahive/db/migrations/004_containers.sql:6-21` — `containers`-Tabelle.
- `core/src/hydrahive/db/migrations/004_containers.sql:23-24` — Indizes owner + actual_state.
- `core/src/hydrahive/db/migrations/004_containers.sql:26-34` — `container_snapshots`-Tabelle + Index (ungenutzt).
- `core/src/hydrahive/db/migrations/005_project_assignments.sql:8,11` — `project_id`-Spalte + Index.

### Tests
- `core/tests/test_container_image_validation.py` — IMAGE_RE-Allowlist + `--`-Separator-Härtung (Issue #185). Einziger dedizierter Container-Test.

### Frontend
- `frontend/src/features/containers/api.ts` — API-Client.
- `frontend/src/features/containers/types.ts` — Typen.
- `frontend/src/features/containers/ContainersPage.tsx` — Übersicht.
- `frontend/src/features/containers/ContainerCard.tsx` — Karte.
- `frontend/src/features/containers/ContainerDetailPage.tsx` — Detail mit Tabs.
- `frontend/src/features/containers/CreateContainerDialog.tsx` — Create-Modal.
- `frontend/src/features/containers/EditContainerDialog.tsx` — Edit-Modal.
- `frontend/src/features/containers/_containerDialogHelpers.tsx` — Field/RadioCard.
- `frontend/src/features/containers/ConsolePane.tsx` — xterm.js + WS.
- `frontend/src/features/containers/ContainerConsoleModal.tsx` — Console-Modal.
- `frontend/src/features/containers/ContainerLogPane.tsx` — Log-Viewer.
- `frontend/src/features/containers/ContainerStatsPane.tsx` — Stats.
- `frontend/src/features/containers/ContainerConfigPane.tsx` — Config-Viewer.
- `frontend/src/features/containers/StatusBadge.tsx` — Status-Pille.
- `frontend/src/App.tsx:76-77` — Routen.
- `frontend/src/i18n/index.ts:28,61,79,90,108` — i18n-Namespace.
- `frontend/src/i18n/locales/en/containers.json`, `.../de/containers.json` — Übersetzungen.
- `frontend/src/i18n/locales/en/errors.json:67-69,121-133` — Container/incus-Fehlercodes.
- `frontend/src/shared/nav-config.ts:46` — Sidebar.
- `frontend/src/shared/colors.ts:23` — Farb-Map.

### Installer
- `installer/modules/70-containers.sh` — incus-Install + dir-Storage-Preseed + images-Remote + default-Profil (privileged/nesting) + incus-admin-Gruppe + Service-`SupplementaryGroups` + br0-Check.

### SPEC
- `SPEC.md:561-595` — Container-Management-Spezifikation.

---

## WARUM

### incus-CLI statt REST-API
Bewusste Entscheidung (`incus_client.py:1-10`): die REST-API über Unix-Socket
wäre sauberer, aber die CLI ist robust und funktioniert mit jeder incus-Version.
Konsequenz: jeder Op ist ein Subprocess-Fork; Fehler werden aus stderr-Strings
geparst (z.B. `"is not running"`, `"already running"`, `"not found"` →
toleriert). **Wenn incus seine Fehlermeldungen ändert, brechen diese
String-Checks still** (`incus_client.py:108,114,129`).

### Flag-Injection-Härtung (Issue #185) — kritische Invariante
`body.image` und `body.name` landen als Positional-Args an einem **root-laufenden**
Subprocess (`incus launch`). Ohne Schutz könnte ein authentifizierter Non-Admin
über einen `:`/`-`-haltigen Wert Flags injizieren (`--target`, `--project`,
`--profile`). Zwei Verteidigungslinien:
1. `IMAGE_RE`/`NAME_RE`-Allowlist (beide Teile MÜSSEN alphanumerisch beginnen,
   kein führendes `-`, `models.py:41-45`).
2. `--`-Separator in `launch` VOR den Positional-Args, Optionen davor
   (`incus_client.py:69-76`). Test erzwingt die Reihenfolge
   (`test_container_image_validation.py:49-66`).
**Wenn man die Argument-Konstruktion in `launch` anfasst, muss der `--`-Separator
und die "Optionen-vor-`--`"-Reihenfolge erhalten bleiben.**

### `privileged=True` ist im nested-LXC-Setup Pflicht
`launch` setzt default `security.privileged=true` + `security.nesting=true`
(`incus_client.py:74-75`). Begründung im Docstring (`incus_client.py:62-65`):
Bare-Metal ginge auch unprivileged, aber das entscheidet der Installer global im
default-Profil. **Der Code überschreibt den Default also pro Container** — das
dupliziert die Installer-Profil-Einstellung (`installer/modules/70-containers.sh:58-59`).
Wenn das default-Profil schon privileged ist, sind die `-c`-Flags redundant aber
harmlos. **Es gibt keinen Caller, der `privileged=False` übergibt** — der Parameter
ist effektiv tot.

### br0 = gemeinsame Bridge mit VMs
Container nutzen dieselbe `settings.vms_bridge` (br0) wie VMs (`lifecycle.py:13-14`,
`_infra.py:54`). Bei `bridged` wird eth0 per `config device override`/`add` auf br0
umgehängt (incusbr0 wäre der Default) + Restart, damit Container eine LAN-DHCP-IP
bekommen (`incus_client.py:82-98`). **Wenn br0 fehlt, starten bridged-Container
nicht** — der Installer warnt nur (`70-containers.sh:100-101`). `isolated` entfernt
eth0 komplett (`incus_client.py:99-100`).

### Create ist transaktional über DB+incus
`create_container` legt erst die DB-Zeile an, dann startet `create_and_start`.
**Schlägt der incus-launch fehl, wird die DB-Zeile wieder gelöscht** und 500
zurückgegeben (`containers_crud.py:63-67`). Das verhindert Waisen-Datensätze, die
sonst als "error" hängen blieben. Anders als bei `start`/`stop`/`restart`, wo der
Fehler-State (`actual=error`) bewusst persistiert bleibt.

### Reconciler-Sticky-States
Der Reconciler fasst nur ACTIVE_STATES (running/starting/stopping) an
(`reconciler.py:13,27`). `error`/`stopped`/`created` sind absichtlich "sticky":
ein abgestürzter Container (desired=running, aber weg) wird einmal auf `error`
gesetzt — danach bleibt er error, weil error nicht mehr in ACTIVE_STATES ist. So
flappt der Status nicht im 4s-Takt. **Recovery aus error geht nur über expliziten
Start/Restart durch den User.**

### Console: PTY statt simplem Pipe
Echte interaktive Shell braucht ein TTY (Cursor, Job-Control, ANSI). Deshalb
`pty.openpty()` + `--mode=interactive` (`console.py:39-47`). Resize wird per
`TIOCSWINSZ`-ioctl ans Master-FD durchgereicht (`console.py:95-104`), damit
`vim`/`htop` korrekt rendern. `start_new_session=True` isoliert die Prozess-Gruppe
(sauberes terminate/kill, `console.py:47`).

### WS-Auth über Query-Param
Browser-WebSockets können keinen `Authorization`-Header setzen — daher JWT als
`?token=` (`container_console.py:8-9,38`). Der Token landet damit potenziell in
Server-Logs/Proxy-Logs (Gotcha, aber Browser-Constraint, nicht vermeidbar ohne
Cookie-Auth).

### Name global eindeutig (nicht pro-Owner)
`containers.name UNIQUE` ohne owner-Scope (`004_containers.sql:9`). Begründung
(`004_containers.sql:4`): incus_name == DB-name, und incus-Instanznamen sind
hostweit eindeutig. `name_taken` prüft daher global, nicht pro User
(`db.py:64-75`). **Zwei User können nicht denselben Container-Namen wählen.**

### Edit nur im Ruhezustand
PATCH ist nur erlaubt wenn actual_state ∈ (stopped/created/error)
(`containers_crud.py:86-88`), weil CPU/RAM-Limits + Name nur am gestoppten
Container sicher änderbar sind. Das FE spiegelt das (`EditContainerDialog.tsx:17`)
und zeigt eine Warnung. **Image ist generell read-only** — Image-Wechsel = neuer
Container (Locale: "Re-Create to change image").

### CPU/RAM-Sentinel-Logik
`update_state`/`update_container_config` nutzen `...` (Ellipsis) als "nicht
ändern"-Sentinel und `None` als "explizit auf unbegrenzt setzen"
(`db.py:80,104-106,113-116`). Das FE baut den Patch entsprechend: Checkbox aus →
`clear_cpu=true`/`clear_ram=true`, sonst Wert (`EditContainerDialog.tsx:44-55`,
`containers_crud.py:97-98`). **Wer die Patch-Logik anfasst, muss die drei Zustände
(unverändert / Wert / explizit-null) auseinanderhalten.**

---

## Datenmodell

### Tabelle `containers` (`004_containers.sql:6-21`)
| Spalte | Typ | Bemerkung |
|--------|-----|-----------|
| `container_id` | TEXT PK | uuid7 |
| `owner` | TEXT NOT NULL | Username |
| `name` | TEXT NOT NULL **UNIQUE** | = incus instance name, hostweit eindeutig |
| `description` | TEXT | optional |
| `image` | TEXT NOT NULL | z.B. `images:debian/12` (mit Präfix gespeichert) |
| `cpu` | INTEGER | `limits.cpu`, NULL = unbegrenzt |
| `ram_mb` | INTEGER | `limits.memory`, NULL = unbegrenzt |
| `network_mode` | TEXT NOT NULL DEFAULT `'bridged'` | `bridged`\|`isolated` |
| `desired_state` | TEXT NOT NULL DEFAULT `'stopped'` | `running`\|`stopped` |
| `actual_state` | TEXT NOT NULL DEFAULT `'created'` | created/starting/running/stopping/stopped/error |
| `last_error_code` | TEXT | letzter IncusError-Code |
| `last_error_params` | TEXT | JSON-serialisierte params |
| `created_at` | TEXT NOT NULL | ISO |
| `updated_at` | TEXT NOT NULL | ISO |
| `project_id` | TEXT | (via Migration 005) NULL = keinem Projekt zugewiesen |

Indizes: `idx_containers_owner`, `idx_containers_actual_state`
(`004_containers.sql:23-24`), `idx_containers_project` (`005:11`).

### Tabelle `container_snapshots` (`004_containers.sql:26-34`) — UNGENUTZT
| Spalte | Typ |
|--------|-----|
| `snapshot_id` | TEXT PK |
| `container_id` | TEXT NOT NULL REFERENCES containers ON DELETE CASCADE |
| `name` | TEXT NOT NULL |
| `description` | TEXT |
| `created_at` | TEXT NOT NULL |

Index `idx_csnap_container`. **Keine Code-Referenz im gesamten Backend** —
Snapshots stehen in der SPEC (`SPEC.md:571`) als Funktionsumfang, sind aber nicht
implementiert (kein Endpoint, kein incus_client-Aufruf, kein FE).

### Config-Keys / Env-Vars
- `HH_VMS_BRIDGE` — Bridge-Name für VMs UND Container, Default `br0`
  (`settings/_infra.py:54`). Keine container-spezifische Env-Var.
- incus-Limits (intern gesetzt, keine HH-Config): `limits.cpu=<cpu>`,
  `limits.memory=<ram_mb>MiB`, `security.privileged=true`, `security.nesting=true`
  (`incus_client.py:71-75`).

### Konstanten (Code, keine DB)
- `POLL_INTERVAL_S = 4.0` (`reconciler.py:12`), FE-Polling 3-5s
  (Card 4s, Stats 3s, Detail 5s, List 4s).
- `MIN_CPU/MAX_CPU = 1/16`, `MIN_RAM_MB/MAX_RAM_MB = 64/32768`
  (`models.py:46-49`).
- Console-Default-PTY-Größe 24×80 (`console.py:41`), Read-Buffer 4096
  (`console.py:60`), terminate-Timeout 3s (`console.py:111`).

### WS-Close-Codes (Protokoll)
- `4401` — nicht authentifiziert.
- `4404` — Container nicht gefunden / kein Zugriff.
- `4409` — Container nicht running.
- `4500` — Backend-Fehler (RuntimeError, z.B. incus_missing).
(`container_console.py:41,47,50,71`; FE-Mapping `ConsolePane.tsx:58-61`.)

### IncusError-Codes (in errors.json lokalisiert)
`incus_missing`, `incus_timeout`, `incus_launch_failed`, `incus_start_failed`,
`incus_stop_failed`, `incus_restart_failed`, `incus_delete_failed`,
`container_not_running`, `container_not_found`, `container_no_access`,
`container_name_invalid`, `container_name_taken`, `container_network_mode_invalid`,
`container_must_be_stopped`, plus **`container_image_invalid`** (im Backend
`containers_crud.py:50`, **fehlt aber in `errors.json`** — siehe Offene Enden).
(`frontend/src/i18n/locales/en/errors.json:67-69,121-133`.)

---

## Offene Enden

1. **Snapshots komplett unimplementiert.** Tabelle `container_snapshots`
   (`004_containers.sql:26-34`) existiert, in SPEC als Funktion gelistet
   (`SPEC.md:571` "live-fähig via incus snapshot create"), aber: kein Endpoint,
   kein `incus_client`-Aufruf (`incus snapshot create` fehlt), keine FE-Komponente,
   keine DB-CRUD-Funktion. Tote Tabelle.

2. **`list_images` (`_incus_inspect.py:47-55`) ungenutzt.** Es gibt nur die
   hardcodierte `QUICK_IMAGES`-Liste und freien Custom-Image-Input. Der
   Image-Katalog-Fetch vom Remote wird nirgends aufgerufen — kein
   `/api/containers/images`-Endpoint. `ContainerImage`-dataclass (`models.py:31-37`)
   ebenfalls tot.

3. **`container_image_invalid` fehlt in errors.json.** Backend wirft den Code
   (`containers_crud.py:50`), aber im FE-`errors.json` ist nur
   `container_name_invalid`/`container_network_mode_invalid` gemappt. Beim
   Image-Reject zeigt das UI den rohen Code statt einer Übersetzung. Inkonsistenz
   zwischen Backend-Codes und FE-Locale.

4. **Console-Auth-Gotcha: `_decode` leakt keine `jwt.InvalidTokenError` mehr.**
   `_authenticate` fängt `(ValueError, KeyError, jwt.InvalidTokenError)`
   (`container_console.py:32`), aber `auth._decode` wandelt ungültige/abgelaufene
   Tokens inzwischen in `coded(...)` = `HTTPException` um (`auth.py:30-33`). Die
   wird **nicht** gefangen → eine `HTTPException` propagiert aus `_authenticate`
   heraus, statt sauberer `None`→close(4401). In einem WS-Handler vor `accept()`
   führt eine durchschlagende Exception zu einem unklaren Verbindungsabbruch statt
   zum definierten 4401-Code. **Latenter Bug**, ausgelöst durch einen abgelaufenen
   oder manipulierten Token. (`KeyError` ist hier nur noch für fehlende
   `payload["sub"]`/`["role"]` relevant.)

5. **Farb-Drift `/containers → "sky"` vs. violet/indigo im UI.**
   `colors.ts:23` mappt das Container-Feature auf `"sky"`, aber alle Komponenten
   verwenden durchgehend violet/indigo-Akzente (Buttons, Badges, Links, Terminal-
   Cursor `#a78bfa`). Die `rgbFor("/containers")`-Variable (`--c`) wird zwar in den
   `box`-Containern gesetzt, der sichtbare Akzent ist aber hartkodiert violett.
   Wahrscheinlich Altlast aus früherem Farbschema.

6. **`restart_` überspringt Transition-States.** `lifecycle.restart_`
   (`lifecycle.py:66-72`) setzt direkt `actual=running`, ohne stopping/starting.
   Inkonsistent zu start/stop, die Transition-States setzen. Wenn der incus-restart
   lange dauert, zeigt das UI vorzeitig "running". Außerdem fängt `restart_` keinen
   IncusError ab, um `actual=error` zu setzen — die Route fängt ihn nur für die
   HTTP-Antwort (`containers_ops.py:54-57`), aber der DB-State bleibt am vorigen
   Wert hängen (nicht error).

7. **FE-`Container`-Typ kennt `project_id` nicht** (`types.ts:5-20`), obwohl
   Backend es in jedem `asdict()` mitliefert (`db.py` Container-dataclass hat das
   Feld). Kein Bug, aber stiller Drift — die Projekt-Zuweisung läuft über die
   separate `projects`-Feature-API, nicht über den Container-Typ.

8. **Doppelte `Field`-Komponente.** `_containerDialogHelpers.tsx:1` exportiert
   `Field` (mit hint), `EditContainerDialog.tsx:137` definiert eine eigene lokale
   `Field` (ohne hint). DRY-Bruch — der Create-Dialog nutzt die Helper-Version,
   der Edit-Dialog seine eigene.

9. **`update_state` mit `desired=None`-Default-Verwirrung.** Der `desired`-Param
   nutzt `None` als "nicht ändern" (`db.py:83`), während `error_code`/`error_params`
   `...` als Sentinel nutzen. Zwei verschiedene "nicht ändern"-Konventionen in
   derselben Funktion — leicht zu verwechseln beim Erweitern.

10. **Hardcodierte deutsche Strings im FE trotz i18n.** `ContainerCard.tsx:120,126`
    (`title="Bearbeiten"`, confirm `"Container ... wirklich löschen? Daten sind
    weg."`), `CreateContainerDialog.tsx:61,127` ("Neuer Container", "Abbrechen"),
    `EditContainerDialog.tsx:68,76,102,112,123,129` ("Container bearbeiten",
    "unbegrenzt", "Abbrechen", "Speichern"), `ContainersPage.tsx:78` (Tip-Text mit
    fest verdrahtetem "debian/12 ist gut für die meisten Dienste"). Trotz
    vorhandenem `containers`-Namespace nicht durchgängig lokalisiert.

11. **`incus_missing` → 503 bei Create, aber 400 bei start/stop/restart.**
    Create prüft `is_available` explizit und gibt 503 (`containers_crud.py:55-56`),
    während die Ops-Routen den `incus_missing`-IncusError aus `_run` als 400 mappen
    (`containers_ops.py:30-31`). Inkonsistenter Status-Code für denselben
    Grundzustand (incus nicht installiert).

12. **`reconcile_once` lädt bei jedem Tick ALLE Container** (`list_(owner=None)`,
    `reconciler.py:21`) und iteriert linear. Bei vielen Containern + 4s-Intervall
    potenziell teuer (kein LIMIT, kein WHERE actual_state IN ACTIVE_STATES auf
    DB-Ebene — gefiltert wird erst in Python, `reconciler.py:27`). Der Index
    `idx_containers_actual_state` existiert, wird aber nicht genutzt.

13. **Kein Test für Lifecycle/Console/Reconciler.** Einziger dedizierter Test ist
    `test_container_image_validation.py` (Image-Allowlist). Keine Tests für
    create_and_start-Rollback, Reconciler-State-Maschine, Console-PTY oder die
    CRUD-Routen-Auth (Owner-Isolation). Deckt die Security-Härtung ab, nicht die
    Kern-Funktionalität.
