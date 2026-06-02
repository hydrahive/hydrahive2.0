# Plugins & Extensions

> Subsystem-Karte für HydraHive2. Erfasst zwei getrennte, oft verwechselte
> Mechanismen: **Plugins** (Python-Code-Erweiterung des Agenten-Tool-Loops, Git-Hub-basiert)
> und **Extensions** (App-Manager: externe Software-Pakete per Bash-Script oder
> docker-compose installieren). Beide sind Admin-only und im Frontend in
> getrennten Feature-Foldern + Nav-Einträgen.
>
> WICHTIG: "Plugin" und "Extension" sind hier zwei verschiedene Dinge.
> - **Plugin** = lädt Python-`Tool`-Objekte in den Core, damit Agenten neue
>   Tools bekommen. Kommt aus einem Git-Hub-Repo. Code läuft im HydraHive-Prozess.
> - **Extension** = installiert *fremde* Software (Gitea, Ollama, Paperless …)
>   nativ als systemd-Service oder als Docker-Container. Hat nichts mit dem
>   Agenten-Tool-Loop zu tun.

---

## WAS

### Plugin-System — Backend-Bausteine

- **`plugins/__init__.py`** — Public-API-Fassade: re-exportiert `load_all`,
  `REGISTRY`, `LoadedPlugin`, `tool_bridge`. (`plugins/__init__.py:8-12`)
- **`PluginManifest`** (Dataclass) — geparstes `plugin.yaml`. Felder:
  `name`, `version`, `description`, `entry` (default `"__init__"`),
  `requires_core` (optional, **wird nicht enforced**), `author` (optional),
  `permissions: list[str]` (geparst, **noch nicht enforced**). (`plugins/manifest.py:18-26`)
- **`ManifestError`** — Exception für kaputtes/unvollständiges `plugin.yaml`. (`plugins/manifest.py:14`)
- **`PluginManifest.from_dict()`** — Strict-Validierung: Top-Level muss Mapping
  sein, `name`/`version`/`description` Pflicht, `name` darf kein `/` enthalten
  und nicht mit `.` beginnen, `permissions` muss Liste sein. (`plugins/manifest.py:28-49`)
- **`PluginManifest.from_file()`** — liest `plugin.yaml` via `yaml.safe_load`. (`plugins/manifest.py:51-57`)
- **`load_all()`** — Discovery + Load aller Plugins beim Backend-Start.
  Idempotent: leert `REGISTRY` bei Wiederaufruf. (`plugins/loader.py:106-124`)
- **`_discover(plugins_dir)`** — sortiert alle Unterordner mit `plugin.yaml`,
  ignoriert Dotdirs. (`plugins/loader.py:24-32`)
- **`_import_plugin()`** — importiert das Entry-Modul, registriert
  Underscore-Namen als Top-Level-`sys.modules`-Eintrag (damit Plugins
  `from <name>.tools.foo import …` nutzen können). (`plugins/loader.py:43-64`)
- **`_module_name_for()`** — wandelt Bindestriche im Plugin-Namen in
  Underscores für den Python-Import. (`plugins/loader.py:35-40`)
- **`_load_one(plugin_dir)`** — pro-Plugin-Lifecycle: Manifest parsen → Modul
  importieren → `on_load(ctx)` aufrufen → `LoadedPlugin` mit Tools oder Error
  zurückgeben. Crash-isoliert. (`plugins/loader.py:67-103`)
- **`LoadedPlugin`** (Dataclass) — Registry-Eintrag: `name`, `manifest`,
  `module`, `tools: list[Tool]`, `error`. Property `loaded` = `error is None
  and module is not None`. (`plugins/registry.py:16-26`)
- **`REGISTRY`** — Modul-Singleton `dict[str, LoadedPlugin]`. (`plugins/registry.py:29`)
- **`registry.reset()`** — leert `REGISTRY` (vom Loader + Tests genutzt). (`plugins/registry.py:32-34`)
- **`registry.all_plugins()`** — `list(REGISTRY.values())`. (`plugins/registry.py:37-38`)
- **`registry.get(name)`** — Lookup nach Name. (`plugins/registry.py:41-42`)
- **`PluginContext`** (Dataclass) — schmales Interface, das ein Plugin in
  `on_load(ctx)` bekommt: `plugin_name`, `plugin_dir`, `logger`. (`plugins/context.py:15-19`)
- **`PluginContext.register_tool(tool)`** — Plugin meldet ein `Tool` an.
  Verweigert nicht-`Tool`-Objekte (TypeError) und Doppel-Namen (ValueError). (`plugins/context.py:22-36`)
- **`PluginContext.tools`** (Property) — defensive Kopie der registrierten Tools. (`plugins/context.py:38-40`)

### Plugin-Tool-Bridge — Anschluss an den Agenten-Tool-Loop

- **Namespacing**: `plugin__<plugin-name>__<tool-name>` (analog zu MCP).
  Konstanten `PREFIX="plugin__"`, `SEP="__"`. (`plugins/tool_bridge.py:14-15`)
- **`make_tool_name(plugin, tool)`** — baut qualifizierten Namen. (`plugins/tool_bridge.py:18-19`)
- **`parse_tool_name(qualified)`** — zerlegt qualifizierten Namen → `(plugin, tool)`
  oder `None` wenn kein Plugin-Tool. (`plugins/tool_bridge.py:22-30`)
- **`all_tool_meta()`** — alle Plugin-Tools geladener Plugins mit `name`,
  `description`, `category="plugin:<name>"`. Für `_meta/tools` + Validierung. (`plugins/tool_bridge.py:33-45`)
- **`schemas_for(qualified_names)`** — Anthropic-Format-Tool-Schemas
  (`name`/`description`/`input_schema`) für die angeforderten Plugin-Tools. (`plugins/tool_bridge.py:48-66`)
- **`call(qualified_name, args, tool_ctx)`** — routet einen Plugin-Tool-Call,
  führt `tool.execute()` aus, fängt Crashes ab. `None` = nicht für uns. (`plugins/tool_bridge.py:69-85`)

### Plugin-Hub-Client (Git-basiert)

- **`refresh()`** — `git clone --depth=1 --filter=blob:none` beim ersten Mal,
  sonst `git pull --ff-only`. Idempotent. (`plugins/hub_client.py:38-56`)
- **`read_hub_index()`** — liest `hub.json` aus dem Cache, ruft `refresh()` bei
  Bedarf. (`plugins/hub_client.py:59-67`)
- **`plugin_source_path(plugin_path)`** — absoluter Pfad eines Plugin-Source-Dirs
  im Cache, mit Path-Escape-Schutz. (`plugins/hub_client.py:70-77`)
- **`HubError`** — Exception bei nicht-erreichbarem/kaputtem Hub-Repo. (`plugins/hub_client.py:25-26`)
- **`_run_git(args, cwd)`** — git-Subprocess mit 60 s Timeout. (`plugins/hub_client.py:29-35`)

### Plugin-Installer

- **`install(name)`** — kopiert Plugin aus Cache ins lokale Plugin-Verzeichnis,
  ruft `loader.load_all()`, prüft auf Loader-Fehler. (`plugins/installer.py:58-75`)
- **`uninstall(name)`** — entfernt Plugin-Verzeichnis/Symlink, ploppt aus
  `REGISTRY`, setzt `restart_recommended=True`. (`plugins/installer.py:78-86`)
- **`update(name)`** — `hub_client.refresh()` + neu kopieren, `restart_recommended=True`. (`plugins/installer.py:89-102`)
- **`InstallResult`** (Dataclass) — `name`, `version`, `restart_recommended`. (`plugins/installer.py:28-32`)
- **`InstallError`** — Exception. (`plugins/installer.py:24-25`)
- **`_cache_path_for(name)`** — findet Plugin-Source im Cache via `hub.json`-Eintrag. (`plugins/installer.py:35-42`)
- **`_local_path_for(name)`** — Zielpfad im `plugins_dir`. (`plugins/installer.py:45-47`)
- **`_remove_existing(dst)`** — räumt Symlink oder Dir weg. (`plugins/installer.py:50-55`)

### Plugin-API-Endpoints (`/api/plugins`, alle Admin-only)

- **`GET /api/plugins/hub`** — verfügbare Plugins aus dem Hub-Index
  (`schema_version`, `updated`, `plugins[]`). (`api/routes/plugins.py:28-43`)
- **`GET /api/plugins/installed`** — lokal geladene Plugins mit Status
  (`name`, `version`, `description`, `loaded`, `error`, `tools[]`). (`api/routes/plugins.py:46-58`)
- **`POST /api/plugins/install`** — Body `{name}`; `refresh()` + `install()`. (`api/routes/plugins.py:61-77`)
- **`POST /api/plugins/uninstall`** — Body `{name}`; entfernt Plugin. (`api/routes/plugins.py:80-92`)
- **`POST /api/plugins/update`** — Body `{name}`; Hub-Cache pullen + neu kopieren. (`api/routes/plugins.py:95-110`)
- **`PluginAction`** (Pydantic-Body) — `{name: str}` für alle POST-Routen. (`api/routes/plugins.py:24-25`)

### Plugin-Frontend (`features/plugins/`)

- **`PluginsPage.tsx`** — Seite mit zwei Tabs (`hub` / `installed`),
  Restart-Button, Restart-Hint-Banner. (`features/plugins/PluginsPage.tsx:11-94`)
- **`HubCard`** — eine Hub-Plugin-Karte: Name, Version, Author, Beschreibung,
  Tags, "Installieren"/"Neu installieren"-Button, "installiert"-Badge. (`features/plugins/PluginCard.tsx:14-47`)
- **`InstalledCard`** — eine installierte-Plugin-Karte: `loaded`/`Fehler`-Badge,
  Error-Text, Tool-Chips, "Aktualisieren"-/"Entfernen"-Buttons. (`features/plugins/PluginCard.tsx:56-108`)
- **`usePlugins()`** (Hook) — State (`hub`, `installed`, `hubError`, `busyName`,
  `restartHint`) + Handler (`handleInstall`/`handleUninstall`/`handleUpdate`),
  `loadInstalled`/`loadHub`. (`features/plugins/usePlugins.ts:6-68`)
- **`pluginsApi`** — `hub`/`installed`/`install`/`uninstall`/`update`. (`features/plugins/api.ts:4-10`)
- **Types**: `HubPlugin`, `HubIndex`, `InstalledPlugin`, `InstallResponse`. (`features/plugins/types.ts:1-30`)
- **i18n**: Namespace `plugins`, DE + EN. (`i18n/locales/{de,en}/plugins.json`)
- **Nav**: `/plugins`, Icon `Puzzle`, Gruppe `automation`, `roles:["admin"]`. (`shared/nav-config.ts:43`)
- **Farbe**: `/plugins` → `yellow`. (`shared/colors.ts:29`)

### Extensions (App Manager) — Backend-API (`/api/admin/extensions`, alle Admin-only)

- **`POST /api/admin/extensions/install-docker`** — SSE-Stream: stellt sicher
  dass Docker-Engine läuft (installiert nur wenn nötig). (`api/routes/extensions.py:35-39`)
- **`GET /api/admin/extensions`** — Liste aller Extensions mit berechnetem
  Status. (`api/routes/extensions.py:42-45`)
- **`GET /api/admin/extensions/credentials`** — gespeicherte Auto-Credentials
  (`*.credentials.json`). (`api/routes/extensions.py:48-60`)
- **`GET /api/admin/extensions/{ext_id}/validate?mode=`** — Manifest-Validierung,
  `{valid, errors[]}`. (`api/routes/extensions.py:63-67`)
- **`POST /api/admin/extensions/{ext_id}/install`** — Body `{params, mode}`;
  SSE-Stream der Installation (native Script oder docker-compose up). (`api/routes/extensions.py:70-123`)
- **`POST /api/admin/extensions/{ext_id}/uninstall`** — Body `{mode}`; SSE-Stream
  (native Uninstall-Script oder `docker compose down`). (`api/routes/extensions.py:126-170`)
- **`POST /api/admin/extensions/{ext_id}/docker/{action}`** — `start`/`stop`/`restart`
  für laufende Docker-Extensions, SSE-Stream. (`api/routes/extensions.py:173-189`)

### Extensions — Backend-Hilfsmodule

- **`_extensions_runner.py`** — Manifest-Loading + Validierung; re-exportiert
  Status/Stream-API für externe Importer. (`api/routes/_extensions_runner.py`)
  - `load_manifests()` — alle `*.json`-Manifeste, dedupliziert nach `id`,
    sortiert nach `_MANIFEST_ORDER` dann alphabetisch. (`api/routes/_extensions_runner.py:58-71`)
  - `validate_manifest(manifest, mode)` — Pflichtfelder, Script-Existenz/leer,
    Compose-Existenz, Docker-Binary, **Dangerous-Pattern-Scan im Script**. (`api/routes/_extensions_runner.py:74-101`)
  - `_DANGEROUS_PATTERNS` — `rm -rf /`, `curl|bash`, `wget|bash`, `mkfs`,
    `dd of=/dev/`. (`api/routes/_extensions_runner.py:31-38`)
  - `_MANIFEST_ORDER` — bevorzugte Sortier-Reihenfolge. (`api/routes/_extensions_runner.py:40-43`)
  - `_manifests_dir()` / `_scripts_base()` — Pfad-Resolver mit Fallback auf
    `<repo>/extensions`. (`api/routes/_extensions_runner.py:46-55`)
  - `__getattr__` — Legacy-Lesezugriff für `_docker_available`/`_docker_binary`. (`api/routes/_extensions_runner.py:105-109`)
- **`_extensions_status.py`** — Docker-Detection + Health-Checks + Status-Aggregation.
  - `docker_binary_exists()` — `which docker`, gecacht. (`api/routes/_extensions_status.py:29-38`)
  - `docker_available()` — `docker info`, gecacht. (`api/routes/_extensions_status.py:41-52`)
  - `reset_docker_cache()` — invalidiert beide Caches. (`api/routes/_extensions_status.py:22-27`)
  - `_check_installed(manifest)` — `installed_check`-Pfad existiert. (`api/routes/_extensions_status.py:57-59`)
  - `_check_docker_running(manifest)` — `docker ps --filter name=…`. (`api/routes/_extensions_status.py:62-73`)
  - `_check_service_active(manifest)` — `systemctl is-active <service>`. (`api/routes/_extensions_status.py:76-87`)
  - `_check_health(manifest, mode)` — HTTP-GET auf `health_url`, `<500` = healthy,
    leere URL = healthy. (`api/routes/_extensions_status.py:90-100`)
  - `_docker_marker_path(manifest)` — `.{id}.docker_installed`-Marker. (`api/routes/_extensions_status.py:103-104`)
  - `_check_docker_marker(manifest)` — Marker-Existenz. (`api/routes/_extensions_status.py:107-108`)
  - `extension_status(manifest)` — aggregierter Status, siehe WIE. (`api/routes/_extensions_status.py:111-151`)
- **`_extensions_stream.py`** — Subprocess-Streaming.
  - `stream_script(script_path, env)` — führt Install/Uninstall-Bash via
    `sudo -n /bin/bash` aus, streamt Zeilen. Env-Vars über Temp-Wrapper-Script
    (sudo strippt env). (`api/routes/_extensions_stream.py:11-56`)
  - `stream_docker(compose_file, action, env)` — `docker compose up/down/start/
    stop/restart`, Env über Temp-`.env`-Datei. (`api/routes/_extensions_stream.py:59-129`)
- **`_extensions_docker.py`** — Docker-Engine-Installer.
  - `install_docker_engine_stream()` — prüft `which docker`, installiert
    via `curl get.docker.com | sh` wenn nötig, `systemctl enable --now docker`,
    `usermod -aG docker`. (`api/routes/_extensions_docker.py:35-80`)
  - `_sudo(parts)` — prefixt `sudo -n` wenn nicht root. (`api/routes/_extensions_docker.py:14-15`)
  - `_run(cmd)` — Subprocess, sammelt Zeilen. (`api/routes/_extensions_docker.py:18-32`)
- **`_extensions_helpers.py`** — Pfad/Manifest/Params/Credentials.
  - `scripts_base()` — Scripts-Wurzel (Settings oder Repo-Fallback). (`api/routes/_extensions_helpers.py:19-22`)
  - `find_manifest(ext_id)` — Manifest nach `id`, sonst 404. (`api/routes/_extensions_helpers.py:25-29`)
  - `resolve_params(manifest, user_params)` — füllt `auto_generate: hex:N`-Felder
    via `secrets.token_hex(N)` wenn leer. (`api/routes/_extensions_helpers.py:32-42`)
  - `write_docker_credentials(manifest, params)` — schreibt `{id}.credentials.json`
    (URL + Param-Werte, Secrets markiert), chmod 640. (`api/routes/_extensions_helpers.py:45-85`)

### Extensions — Frontend (`features/extensions/`)

- **`ExtensionsPage.tsx`** — Seite mit Kategorie-Sidebar (Desktop) / Dropdown
  (Mobile), Extension-Grid, Docker-Banner + Docker-Install-Log (nur im
  `dockertools`-Tab), Install/Uninstall-Modal. (`features/extensions/ExtensionsPage.tsx:17-206`)
- **`ExtensionCard`** — eine Extension-Karte: Icon, Name, `StatusBadge`,
  Docker-Badge, Mode-Toggle (Native/Docker, nur wenn Docker verfügbar +
  `docker`-Block + nicht installiert), Install/Open/Start/Stop/Restart/Uninstall. (`features/extensions/ExtensionCard.tsx:56-157`)
- **`StatusBadge`** — `not_installed`/`active`/`running_unreachable`/`stopped`. (`features/extensions/ExtensionCard.tsx:26-48`)
- **`ExtIcon`** — Icon-Map (lucide), Fallback `Package`. (`features/extensions/ExtensionCard.tsx:14-24`)
- **`InstallModal`** — Param-Eingabe → Live-Log-Stream → Done/Fail. Phasen
  `params`/`running`/`done`. (`features/extensions/InstallModal.tsx:16-128`)
- **`fetchExtensions()`** — `GET /admin/extensions`. (`features/extensions/api.ts:7-9`)
- **`authHeaders()`** — Bearer-Token aus `useAuthStore`. (`features/extensions/api.ts:11-14`)
- **`streamAction()`** — POST + manuelles SSE-Reading via `fetch`+`ReadableStream`,
  Callbacks `onLine`/`onDone`/`onError`, abbrechbar. (`features/extensions/api.ts:16-59`)
- **Types**: `InstallParam`, `DockerConfig`, `Extension`, `InstallMode`,
  `CATEGORIES`. (`features/extensions/types.ts`)
- **`CATEGORIES`** — 10 Kategorien: all, tools, dev, ai, network, security,
  productivity, media, gaming, dockertools (Labels hart-codiert deutsch). (`features/extensions/types.ts:42-53`)
- **`ExtensionCredentials.tsx`** — eigene Komponente unter `features/credentials/`,
  liest `GET /admin/extensions/credentials`, zeigt Felder mit Secret-Toggle. (`features/credentials/ExtensionCredentials.tsx:38-92`)
- **i18n**: Namespace `extensions`, DE + EN. (`i18n/locales/{de,en}/extensions.json`)
- **Nav**: `/extensions`, Icon `Package`, Gruppe `settings`, `roles:["admin"]`. (`shared/nav-config.ts:54`)
- **Farbe**: Extension-Karten nutzen `rgbFor("/mcp")` (kein eigener `/extensions`-Farbeintrag).

### Extension-Catalog (Manifest-Dateien, `extensions/manifests/*.json`)

Aktuell 32 Manifeste (mehr als der SPEC-Katalog): adguard-home, anythingllm,
bookstack, codeserver, gitea, golang, headscale, heimdall, hyos, java-openjdk,
mailcow, minecraft, monica-crm, nodejs, ollama, paperless-ngx, pihole, plex,
radarr, radicale, rust, sabnzbd, searxng, shadowbroker, skill-seekers, sonarr,
trinitycore-335, valheim, vaultwarden, vikunja, webmin.

- **Script-Verzeichnisse**: `extensions/install/*.sh`, `extensions/uninstall/*.sh`,
  `extensions/docker/*.compose.yml`.

---

## WIE

### Plugin-Lifecycle (Backend-Start → Tool im Agenten verfügbar)

1. **Backend-Start** ruft in `lifespan` `plugin_system.load_all()`. (`api/lifespan.py:119`)
2. `load_all()` leert `REGISTRY`, legt `settings.plugins_dir`
   (`<data_dir>/plugins`) an, `_discover()` findet alle Unterordner mit
   `plugin.yaml`. (`plugins/loader.py:106-117`)
3. Pro Plugin `_load_one()`:
   a. `PluginManifest.from_file()` parst `plugin.yaml` (strict). Fehler →
      `LoadedPlugin(error=…)`, kein Crash. (`plugins/loader.py:67-72`)
   b. `_import_plugin()` registriert den Underscore-Namen als Top-Level-Modul
      in `sys.modules` und führt `__init__.py` aus. (`plugins/loader.py:74-78`)
   c. `getattr(module, "on_load")` muss callable sein, sonst Error-Plugin. (`plugins/loader.py:80-85`)
   d. `PluginContext` wird gebaut und an `on_load(ctx)` übergeben. Das Plugin
      ruft darin `ctx.register_tool(tool)` für jedes Tool. (`plugins/loader.py:87-99`)
   e. Erfolg → `LoadedPlugin(tools=ctx.tools)`. (`plugins/loader.py:101-103`)
4. **Agenten-Tool-Loop** (Runner) zur Laufzeit:
   - `runner.py` baut die Tool-Schemas: `plugin_bridge.schemas_for(local_tools)`
     fügt Plugin-Tool-Schemas zu Core- + MCP-Schemas. (`runner/runner.py:101-102`)
   - LLM ruft ein Tool `plugin__<name>__<tool>`.
   - `dispatcher.py` erkennt `tool_name.startswith(plugin_bridge.PREFIX)` und
     routet via `plugin_bridge.call()`. (`runner/dispatcher.py:78-82`)
   - `call()` parst Namen → findet Plugin in `REGISTRY` → `tool.execute(args, ctx)`,
     Crash → `ToolResult.fail("Plugin-Crash: …")`. (`plugins/tool_bridge.py:69-85`)
5. **Validierung beim Agent-Anlegen/Editieren**: `validate_tools()` akzeptiert
   einen Tool-Namen nur wenn er in `TOOL_REGISTRY`, in `plugin_bridge.all_tool_meta()`
   oder in `OPTIONAL_TOOLS` ist. (`agents/_validation.py:29-42`)
6. **Tool-Katalog-Endpoint**: `GET /agents`-nahes Meta liefert Core-Tools +
   `plugin_bridge.all_tool_meta()`. (`api/routes/agents.py:37`)
7. **Buddy-Config**: `all_tools` = Core-Tool-Namen + Plugin-Tool-Namen. (`buddy/_config.py:21-24`)

### Plugin-Install-Flow (Admin-UI → Hub → lokal)

1. **Hub-Tab öffnen** → `usePlugins` ruft `loadHub()` → `GET /plugins/hub`.
   Backend: `hub_client.refresh()` (git clone/pull) + `read_hub_index()`. (`features/plugins/usePlugins.ts:19-27`, `api/routes/plugins.py:28-43`)
2. **Installieren-Klick** → `handleInstall(name)` → `POST /plugins/install {name}`. (`features/plugins/usePlugins.ts:31-40`)
3. Backend: `hub_client.refresh()` → `installer.install(name)`:
   - `_cache_path_for()` schlägt Source-Pfad in `hub.json` nach.
   - `_remove_existing()` + `shutil.copytree(src, dst, symlinks=False)`.
   - `loader.load_all()` lädt **alle** Plugins neu (nicht nur das eine).
   - Bei Loader-Fehler → `InstallError("plugin_load_failed:…")` (Plugin bleibt
     liegen, damit User den Fehler im UI sieht). (`plugins/installer.py:58-75`)
4. Erfolg → `InstallResult` (kein `restart_recommended` bei frischem Install,
   weil sofort geladen). Frontend re-fetcht `loadInstalled()`. (`features/plugins/usePlugins.ts:33-37`)
5. **Update/Uninstall** setzen `restart_recommended=True` → Frontend zeigt
   Restart-Hint-Banner + Restart-Button (`useRestart`/`RestartModal`). (`features/plugins/PluginsPage.tsx:43-51`)

### Extension-Status-Berechnung (`extension_status`)

Zustandsmaschine in `extension_status()` (`api/routes/_extensions_status.py:111-151`):

```
docker_running = docker ps filter name == service_name
docker_marker  = .{id}.docker_installed exists
native_mode    = installed_check exists AND preferred_mode != "docker"

IF docker_running OR docker_marker:
    install_mode = "docker"
    active  = docker_running
    healthy = health(docker) if docker_running else False
ELIF native_mode:
    install_mode = "native"
    active  = systemctl is-active service
    healthy = health(native) if active else False
ELSE:
    install_mode = None; active=False; healthy=False

installed = docker_running OR docker_marker OR native_mode
open_url  = url_file-Inhalt (falls gesetzt) sonst manifest.open_url
docker_available = docker_binary_exists()
```

- `preferred_mode: "docker"` schaltet `installed_check` für native ab, weil das
  Data-Verzeichnis nach `docker compose down` bestehen bleibt (sonst würde es
  fälschlich "native installiert" anzeigen). (`api/routes/_extensions_status.py:114-117`)
- `url_file` erlaubt dynamische URLs (z. B. macvlan-IP nach Install). (`api/routes/_extensions_status.py:132-141`)

### Extension-Install-Flow (native)

1. **Install-Klick** → `ExtensionCard.onInstall(mode)` öffnet `InstallModal`
   mit `mode`. (`features/extensions/ExtensionCard.tsx:114`)
2. Falls sichtbare Params: Phase `params`, sonst direkt `running`. Sichtbar =
   Param ohne `auto_generate` oder `required`. (`features/extensions/InstallModal.tsx:19-22`)
3. `streamAction(id, "install", params, …, mode)` → `POST /admin/extensions/
   {id}/install {params, mode}`. (`features/extensions/api.ts:16-59`)
4. Backend `install_extension()`:
   - `find_manifest()` + `validate_manifest()` (422 bei Fehlern).
   - `resolve_params()` füllt `hex:N`-Auto-Felder.
   - native: `stream_script(scripts_base()/install_script, params)` → SSE-Frames
     `{line}`, am Ende `{done:true}`. (`api/routes/extensions.py:70-123`)
5. `stream_script()` baut das Kommando je nach UID:
   - root: `["/bin/bash", script]`.
   - non-root + env: schreibt Temp-Wrapper-Script (`export VAR=…; exec /bin/bash
     script`), führt `sudo -n /bin/bash <wrapper>` aus (sudoers erlaubt nur
     `/bin/bash`), räumt Wrapper im `finally` weg. (`api/routes/_extensions_stream.py:11-56`)
6. Frontend parst SSE-Zeilen, färbt `[OK]`/`[FEHLER]`/`[WARN]`, scrollt mit. (`features/extensions/InstallModal.tsx:98-111`)

### Extension-Install-Flow (Docker)

1. Mode `docker`: `install_extension()` → `stream_docker(compose_file, "up",
   env=params)`. (`api/routes/extensions.py:90-114`)
2. `stream_docker` (action `up`):
   - schreibt Params in Temp-`.env` (chmod 600), Kommando
     `docker compose -f … --env-file … up -d --pull always` (sudo strippt env,
     daher `.env`-Datei statt Subprocess-env). (`api/routes/_extensions_stream.py:69-92`)
   - setzt vorher `sysctl net.ipv4.ip_unprivileged_port_start=0` (für
     unprivilegierte Ports). (`api/routes/_extensions_stream.py:85-92`)
3. Nach `[OK]`: Route schreibt Docker-Marker (`.{id}.docker_installed`) +
   `write_docker_credentials()`. (`api/routes/extensions.py:99-111`)
4. **Docker-Uninstall**: `docker compose down --volumes --remove-orphans` +
   löscht Credentials-Datei + Marker. (`api/routes/extensions.py:137-156`, `_extensions_stream.py:93-99`)
5. **Docker start/stop/restart**: `docker compose <action>` (kein volumes-Flag,
   leere `.env`). (`api/routes/_extensions_stream.py:100-106`)

### Docker-Engine-Installation

1. `dockertools`-Tab, Docker nicht da → "Docker installieren"-Button →
   `POST /admin/extensions/install-docker` (SSE). (`features/extensions/ExtensionsPage.tsx:47-83`)
2. `install_docker_engine_stream()`: `which docker` → wenn fehlt
   `curl get.docker.com | sh` → `systemctl enable --now docker` →
   `usermod -aG docker <user>` → `reset_docker_cache()` → `[OK]`. (`api/routes/_extensions_docker.py:35-80`)

---

## WO

### Plugin-System (Backend)
- `core/src/hydrahive/plugins/__init__.py:1-12` — Public-API-Fassade
- `core/src/hydrahive/plugins/manifest.py:14` — `ManifestError`
- `core/src/hydrahive/plugins/manifest.py:18-49` — `PluginManifest` + `from_dict`
- `core/src/hydrahive/plugins/manifest.py:51-57` — `from_file`
- `core/src/hydrahive/plugins/loader.py:24-32` — `_discover`
- `core/src/hydrahive/plugins/loader.py:35-40` — `_module_name_for`
- `core/src/hydrahive/plugins/loader.py:43-64` — `_import_plugin`
- `core/src/hydrahive/plugins/loader.py:67-103` — `_load_one`
- `core/src/hydrahive/plugins/loader.py:106-124` — `load_all`
- `core/src/hydrahive/plugins/registry.py:16-26` — `LoadedPlugin`
- `core/src/hydrahive/plugins/registry.py:29` — `REGISTRY`
- `core/src/hydrahive/plugins/registry.py:32-42` — `reset`/`all_plugins`/`get`
- `core/src/hydrahive/plugins/context.py:15-40` — `PluginContext` + `register_tool` + `tools`

### Plugin-Tool-Bridge
- `core/src/hydrahive/plugins/tool_bridge.py:14-15` — `PREFIX`/`SEP`
- `core/src/hydrahive/plugins/tool_bridge.py:18-30` — `make_tool_name`/`parse_tool_name`
- `core/src/hydrahive/plugins/tool_bridge.py:33-45` — `all_tool_meta`
- `core/src/hydrahive/plugins/tool_bridge.py:48-66` — `schemas_for`
- `core/src/hydrahive/plugins/tool_bridge.py:69-85` — `call`

### Plugin-Hub + Installer
- `core/src/hydrahive/plugins/hub_client.py:25-26` — `HubError`
- `core/src/hydrahive/plugins/hub_client.py:29-35` — `_run_git`
- `core/src/hydrahive/plugins/hub_client.py:38-56` — `refresh`
- `core/src/hydrahive/plugins/hub_client.py:59-67` — `read_hub_index`
- `core/src/hydrahive/plugins/hub_client.py:70-77` — `plugin_source_path` (Path-Escape-Schutz)
- `core/src/hydrahive/plugins/installer.py:24-32` — `InstallError`/`InstallResult`
- `core/src/hydrahive/plugins/installer.py:35-55` — `_cache_path_for`/`_local_path_for`/`_remove_existing`
- `core/src/hydrahive/plugins/installer.py:58-102` — `install`/`uninstall`/`update`

### Plugin-Routes + Integration
- `core/src/hydrahive/api/routes/plugins.py:21` — Router-Prefix `/api/plugins`
- `core/src/hydrahive/api/routes/plugins.py:24-110` — alle 5 Endpoints
- `core/src/hydrahive/api/main.py:41,115` — Import + `include_router(plugins_router)`
- `core/src/hydrahive/api/lifespan.py:119` — `plugin_system.load_all()`
- `core/src/hydrahive/runner/runner.py:24,101-102` — Plugin-Schemas in Tool-Loop
- `core/src/hydrahive/runner/dispatcher.py:10,78-82` — Plugin-Tool-Routing
- `core/src/hydrahive/agents/_validation.py:3,32-42` — Tool-Validierung gegen Plugin-Namen
- `core/src/hydrahive/buddy/_config.py:6,21-24` — Plugin-Tools in Buddy-Tool-Liste
- `core/src/hydrahive/api/routes/agents.py:19,37` — Plugin-Tools im Tool-Meta-Katalog
- `core/src/hydrahive/backup/_paths.py:21` — `data/plugins` im Backup-Set

### Plugin-Frontend
- `frontend/src/features/plugins/PluginsPage.tsx:11-94`
- `frontend/src/features/plugins/PluginCard.tsx:14-108` — `HubCard` + `InstalledCard`
- `frontend/src/features/plugins/usePlugins.ts:6-68`
- `frontend/src/features/plugins/api.ts:4-10`
- `frontend/src/features/plugins/types.ts:1-30`
- `frontend/src/App.tsx:90` — Route `plugins`
- `frontend/src/shared/nav-config.ts:43` — Nav-Eintrag
- `frontend/src/shared/colors.ts:29` — `/plugins → yellow`
- `frontend/src/i18n/locales/de/plugins.json`, `…/en/plugins.json`

### Extensions (Backend)
- `core/src/hydrahive/api/routes/extensions.py:30` — Router-Prefix `/api/admin/extensions`
- `core/src/hydrahive/api/routes/extensions.py:32` — `_SSE_HEADERS`
- `core/src/hydrahive/api/routes/extensions.py:35-189` — alle 7 Endpoints
- `core/src/hydrahive/api/routes/_extensions_runner.py:31-43` — Patterns + Sort-Order
- `core/src/hydrahive/api/routes/_extensions_runner.py:58-101` — `load_manifests`/`validate_manifest`
- `core/src/hydrahive/api/routes/_extensions_status.py:18-52` — Docker-Detection + Cache
- `core/src/hydrahive/api/routes/_extensions_status.py:57-108` — Status-Checks
- `core/src/hydrahive/api/routes/_extensions_status.py:111-151` — `extension_status`
- `core/src/hydrahive/api/routes/_extensions_stream.py:11-56` — `stream_script`
- `core/src/hydrahive/api/routes/_extensions_stream.py:59-129` — `stream_docker`
- `core/src/hydrahive/api/routes/_extensions_docker.py:14-80` — Docker-Engine-Install
- `core/src/hydrahive/api/routes/_extensions_helpers.py:19-85` — Pfad/Manifest/Params/Credentials
- `core/src/hydrahive/api/main.py:30,133` — Import + `include_router(extensions_router)`

### Extensions (Frontend + Catalog)
- `frontend/src/features/extensions/ExtensionsPage.tsx:17-206`
- `frontend/src/features/extensions/ExtensionCard.tsx:14-157`
- `frontend/src/features/extensions/InstallModal.tsx:16-128`
- `frontend/src/features/extensions/api.ts:7-59`
- `frontend/src/features/extensions/types.ts:1-53`
- `frontend/src/features/credentials/ExtensionCredentials.tsx:38-92`
- `frontend/src/App.tsx:91` — Route `extensions`
- `frontend/src/shared/nav-config.ts:54` — Nav-Eintrag
- `frontend/src/i18n/locales/de/extensions.json`, `…/en/extensions.json`
- `extensions/manifests/*.json` (32 Manifeste)
- `extensions/install/*.sh`, `extensions/uninstall/*.sh`, `extensions/docker/*.compose.yml`

### Settings/Config (Backend)
- `core/src/hydrahive/settings/_paths.py:35-37` — `plugins_dir` (`<data_dir>/plugins`)
- `core/src/hydrahive/settings/_paths.py:39-41` — `plugin_hub_cache` (`<data_dir>/.plugin-cache/hub`)
- `core/src/hydrahive/settings/_paths.py:43-48` — `plugin_hub_git_url` (Env `HH_PLUGIN_HUB_GIT_URL`)
- `core/src/hydrahive/settings/_infra.py:58-65` — `extensions_manifests_dir` (`<base_dir>/extensions/manifests`), `extensions_install_dir` (`<base_dir>/extensions/install`)

### SPEC-Referenzen
- `SPEC.md:232-247` — Plugin-System
- `SPEC.md:144` — Pro-Plugin-Permission (geplant)
- `SPEC.md:1080-1149` — Extensions App-Manager
- `SPEC.md:1062` — `registry.py` Tool-Registry für Plugin-Andockung

---

## WARUM

### Plugin-System: Invarianten + Annahmen
- **Core wird nie für Plugins angefasst** (CLAUDE.md + SPEC.md:234). Das ganze
  Plugin-System ist eine Andock-Schicht: Plugins reden *nur* über `PluginContext`
  mit dem Core, nie direkt. `register_tool` ist die einzige Schreib-Schnittstelle.
- **Crash-Isolation ist hart eingebaut**: jeder Schritt in `_load_one`
  (Manifest, Import, `on_load`) fängt Exceptions und legt ein Error-`LoadedPlugin`
  ab — ein kaputtes Plugin bricht weder `load_all` noch den Core (SPEC.md:246).
  `loaded`-Property unterscheidet geladen/fehlerhaft.
- **`sys.modules`-Trick** (`_import_plugin`): Der Underscore-Name wird als
  Top-Level-Modul registriert, damit Plugins interne Sub-Imports
  (`from mein_plugin.tools.x import …`) machen können. GOTCHA: das mutiert
  globalen Modul-State. Zwei Plugins, deren Name nach `-`→`_`-Normalisierung
  kollidiert (`my-plugin` vs. `my_plugin`), überschreiben sich gegenseitig.
- **Reload-Limit**: `load_all` ist nominell idempotent (leert `REGISTRY`), aber
  Python cached importierte Module — geänderter Plugin-Code wirkt erst nach
  Prozess-Neustart voll. Deshalb setzen `uninstall`/`update`
  `restart_recommended=True` (`installer.py:86,101`), `install` aber nicht
  (frischer Import). Das ist der Grund für den Restart-Hint im UI.
- **Tool-Namespacing identisch zu MCP** (`plugin__…__…` vs `mcp__…`): der
  Dispatcher entscheidet per Prefix, welcher Bridge der Call gehört
  (`dispatcher.py:78`). Würde man den Prefix ändern, brechen bestehende
  Agent-Tool-Listen + Dispatcher-Routing gleichzeitig.
- **`requires_core` und `permissions` werden geparst aber NICHT enforced** —
  SPEC.md:144 sieht "Pro-Plugin-Permission" vor, aber Manifest liest nur, der
  Loader prüft nichts. Ein Plugin bekommt vollen Core-Zugriff im Prozess.
- **`plugin_source_path` hat Path-Escape-Schutz** (`hub_client.py:74-76`), weil
  `hub.json` aus einem Remote-Repo kommt und `path`-Felder sonst aus dem Cache
  herauszeigen könnten.
- **Hub ist Git, nicht HTTP-API**: clone/pull, kein Auth-Layer. Default-URL ist
  `https://github.com/hydrahive/hydrahive2-plugins.git` (`_paths.py:44-48`);
  privates Repo braucht einen SSH-Key beim Service-User (Doc-Kommentar
  `hub_client.py:6-9` spricht von SSH-URL — der Default ist aber HTTPS,
  leichte Drift).

### Extensions: Invarianten + Annahmen
- **Plugins ≠ Extensions**: Extensions sind ein *App-Manager* (fremde Software),
  kein Code im Agenten-Loop. Verwechslungsgefahr ist hoch, weil beide "install/
  uninstall/update" + Cards + Admin-only haben.
- **Deklarativ**: jede Extension = JSON-Manifest + Bash-Script(s) (+ optional
  compose-yml). Kein Python pro Extension. Neue Extension = Manifest + Script
  ablegen, kein Code-Eingriff.
- **Sudo-Modell**: Backend läuft typischerweise als non-root Service-User.
  sudoers erlaubt nur `/bin/bash` (+ docker/systemctl/sysctl/usermod). Daher die
  **Wrapper-Script-Mechanik** in `stream_script` (env-Vars über exportierendes
  Temp-Script, weil `sudo` Subprocess-env strippt) und **`.env`-Datei** in
  `stream_docker`. Wer den sudoers-Eintrag ändert, bricht alle nativen Installs.
- **`[OK]`/`[FEHLER]`-Sentinels** sind das Vertrags-Protokoll zwischen Streamer
  und Route/Frontend: `stream_script`/`stream_docker` hängen am Ende `[OK]` oder
  `[FEHLER]` an; die Install-Route setzt den Docker-Marker nur wenn eine Zeile
  mit `[OK]` startet (`extensions.py:99-101`); das Frontend färbt nach denselben
  Präfixen. Wer die Sentinel-Strings ändert, bricht Marker-Logik + UI-Farben.
- **Docker-Detection ist gecacht** (`_docker_binary`/`_docker_available` Modul-
  Globals). Nach Docker-Engine-Install muss `reset_docker_cache()` laufen, sonst
  zeigt die Liste weiter "Docker nicht verfügbar" bis Prozess-Neustart
  (`_extensions_docker.py:78`).
- **Dangerous-Pattern-Scan** (`validate_manifest`) ist eine dünne Schutzschicht
  gegen offensichtlich gefährliche Install-Scripts (`rm -rf /`, `curl|bash`).
  GOTCHA/Inkonsistenz: der Docker-Engine-Installer selbst nutzt
  `curl get.docker.com | sh` (`_extensions_docker.py:44`) — das Pattern gilt nur
  für *Extension-Scripts*, nicht für den Engine-Installer.
- **`preferred_mode: "docker"`** existiert, weil docker-only Extensions kein
  natives `installed_check`-Binary haben; ihr Data-Verzeichnis überlebt
  `compose down`, würde sonst fälschlich "native installiert" melden.
- **Marker vs. Volume-Löschung**: Docker-Uninstall macht `down --volumes` (löscht
  Daten!) und entfernt Marker + Credentials. `docker/start|stop|restart` lassen
  Volumes + Marker in Ruhe. Wer `down` mit `restart` verwechselt, löscht Daten.
- **Pfad-Fallbacks**: `scripts_base`/`_manifests_dir` haben Settings-Pfad +
  Repo-relativen Fallback (`parents[5]/extensions`). Verschiebt man die Datei in
  der Verzeichnistiefe, bricht der `parents[5]`-Fallback.

---

## Datenmodell

### Plugin-Manifest (`plugin.yaml`)
| Feld | Pflicht | Bedeutung |
|---|---|---|
| `name` | ja | eindeutiger Name, kein `/`, kein führender `.` |
| `version` | ja | Versions-String |
| `description` | ja | Beschreibung |
| `entry` | nein | Entry-Modul, default `__init__` |
| `requires_core` | nein | Core-Version (geparst, nicht enforced) |
| `author` | nein | Autor |
| `permissions` | nein | `list[str]` (geparst, nicht enforced) |

### Plugin-Hub-Index (`hub.json` im Cache-Repo)
- `schema_version`, `updated`, `plugins: [{ name, version, description, author?,
  path?, requires_core?, tags? }]`. Gelesen in `read_hub_index`, gemappt im
  Frontend als `HubIndex`/`HubPlugin`.

### Plugin-API-Shapes
- `InstalledPlugin`: `{name, version, description, loaded, error, tools[]}`.
- `InstallResponse`: `{name, version, restart_recommended}`.

### LoadedPlugin (in-memory, `REGISTRY`)
- `{name, manifest: PluginManifest|None, module, tools: list[Tool], error}`.

### Extension-Manifest (`extensions/manifests/<id>.json`)
| Feld | Bedeutung |
|---|---|
| `id` | eindeutige ID (Dateiname-Basis, Routen-Param) |
| `name` | Anzeigename |
| `description` | Beschreibung |
| `icon` | lucide-Icon-Name (Frontend-Map, Fallback `Package`) |
| `category` | eine der 10 `CATEGORIES` |
| `install_script` | rel. Pfad zu Bash-Script |
| `uninstall_script` | rel. Pfad (optional) |
| `service` | systemd-Unit-Name (native Aktiv-Check) |
| `health_url` | HTTP-Health-Check |
| `open_url` | Öffnen-Link (`:port/` oder absolut) |
| `installed_check` | Pfad der bei native-Install existieren muss |
| `install_params[]` | `{key,label,type,placeholder?,required,description?,auto_generate?}` |
| `preferred_mode` | `"docker"` schaltet native installed_check ab |
| `url_file` | Pfad für dynamische URL (überschreibt open_url) |
| `docker` | `{compose_file, service_name, health_url?, open_url?}` |

`auto_generate`-Format: `hex:N` → `secrets.token_hex(N)`.

### Extension-Status-Response (`extension_status`, GET /admin/extensions)
- Alle Manifest-Felder + `open_url` (ggf. aus `url_file`) + `installed`,
  `install_mode` (`native`/`docker`/`null`), `active`, `healthy`,
  `docker_available`.

### Extension-Credentials (`<config_dir>/extensions/<id>.credentials.json`)
- Geschrieben: `{extension_id, extension_name, install_mode:"docker",
  fields:[{key,label,value,secret}]}` (chmod 640). (`_extensions_helpers.py:75-83`)
- DRIFT: Frontend `ExtCred` erwartet `{id, name, fields:[{label,value,secret}]}` —
  Keys `id`/`name` vs. geschriebene `extension_id`/`extension_name`
  (siehe Offene Enden).

### Docker-Marker
- `<config_dir>/extensions/.<id>.docker_installed` — leere Datei,
  markiert docker-installiert. (`_extensions_status.py:103-104`)

### Config-Keys / Env-Vars
| Key/Env | Default | Bedeutung |
|---|---|---|
| `settings.plugins_dir` | `<data_dir>/plugins` | lokale Plugin-Installation |
| `settings.plugin_hub_cache` | `<data_dir>/.plugin-cache/hub` | Git-Cache des Hub-Repos |
| `settings.plugin_hub_git_url` | `github.com/hydrahive/hydrahive2-plugins.git` | Hub-Repo |
| `HH_PLUGIN_HUB_GIT_URL` (Env) | — | überschreibt Hub-URL |
| `settings.extensions_manifests_dir` | `<base_dir>/extensions/manifests` | Manifest-Verzeichnis |
| `settings.extensions_install_dir` | `<base_dir>/extensions/install` | Install-Script-Basis |
| `settings.config_dir / "extensions"` | — | Credentials + Docker-Marker |

### Backup
- `data/plugins` ist Teil des Backup-Sets. (`backup/_paths.py:21`)
- Extension-Catalog (`extensions/`) und Credentials (`config_dir/extensions`)
  sind **nicht** explizit im Plugin-Backup-Eintrag (Catalog ist Repo-Teil;
  Config-Dir wird als Ganzes gesichert — siehe SPEC.md:319).

### Tool-Namespacing
- Plugin-Tools im Tool-Loop: `plugin__<plugin-name>__<tool-name>`.

---

## Offene Enden

### Plugins
- **Permissions/`requires_core` nicht enforced**: Manifest parst `permissions`
  und `requires_core`, aber weder Loader noch Bridge prüfen sie. SPEC.md:144
  fordert Pro-Plugin-Permission — derzeit nicht implementiert. Ein Plugin läuft
  mit vollem Prozess-Zugriff. (`manifest.py:26,46`, `loader.py`)
- **`requires_core`-Versions-Gate fehlt komplett** — Feld existiert, wird nie
  gegen die laufende Core-Version geprüft.
- **Doc-Drift Hub-URL**: `hub_client.py:6-9` beschreibt SSH-URL für privates
  Repo, Default ist aber HTTPS-Public-Repo. (`_paths.py:44-48`)
- **`install` lädt alle Plugins neu** (`loader.load_all()`), nicht nur das eine —
  funktioniert, ist aber O(n) bei jedem Install und kann Seiteneffekte bei
  anderen Plugins triggern (deren `on_load` läuft erneut).
- **`-`→`_`-Namenskollision** im `sys.modules`-Trick nicht abgefangen
  (`loader.py:49-61`).
- **Hub-Repo evtl. leer/nicht existent**: Default-Repo
  `hydrahive/hydrahive2-plugins` — wenn es nicht existiert, liefert `/plugins/hub`
  502 (`plugin_hub_unreachable`); UI zeigt nur die Fehlermeldung. Kein
  ausgeliefertes Beispiel-Plugin im Repo gefunden.
- **Keine Tests**: weder `core/tests` noch Frontend-Tests für Plugins gefunden
  (Suche nach `*plugin*`-Tests ergab nur venv-Fremdpakete).

### Extensions
- **Credentials-Shape-Drift (HIGH)**: Backend schreibt `extension_id`/
  `extension_name` (`_extensions_helpers.py:76-77`), Frontend `ExtCred` liest
  `id`/`name` (`ExtensionCredentials.tsx:14-17,80-81`). Folge: Name-Anzeige in
  `ExtensionCredentials` ist `undefined`, Karten erscheinen ohne Titel. Die
  `key`-Felder passen, der Container-Name nicht.
- **Dangerous-Pattern-Scan greift nicht für den Docker-Engine-Installer**, der
  selbst `curl … | sh` nutzt — Inkonsistenz zwischen Policy für Extension-Scripts
  und Engine-Install. (`_extensions_docker.py:44` vs. `_extensions_runner.py:33`)
- **`docker compose down --volumes` löscht Daten** beim Uninstall — kein
  Backup/keine Warnung im Backend, nur Modal-Bestätigung im Frontend.
- **`docker_action` (start/stop/restart) ohne Marker/Status-Schreiben** — der
  Status wird rein über `docker ps` neu berechnet; bei Race (Container fährt
  gerade hoch) kann der Status kurz falsch sein.
- **Keine `*/validate`-Nutzung im Frontend** sichtbar — der Validate-Endpoint
  existiert, wird vom UI aber nicht aktiv aufgerufen (Validierung passiert
  serverseitig vor Install).
- **Sudo-Annahme nicht überall geprüft**: `stream_script`/`stream_docker` fallen
  bei fehlendem passwortlosem sudo nur durch SSE-`[FEHLER]` auf, kein
  Vorab-Check.
- **Kein `/extensions`-Slash-Command** gefunden, obwohl SPEC.md:736 ihn als
  "eigenes Pill-UI" listet — derzeit nur die Nav-Seite, kein Chat-Slash-Command.
- **`open_url` Host-Auflösung uneinheitlich**: Frontend baut
  `http://<window.hostname><open_url>` (`ExtensionCard.tsx:67-74`); Backend baut
  in Credentials `http://<gethostbyname(gethostname())><open_url>`
  (`_extensions_helpers.py:54-60`) — zwei verschiedene Host-Quellen für dieselbe
  URL.
- **Catalog > SPEC-Liste**: 32 Manifeste real (u. a. anythingllm, mailcow, hyos,
  shadowbroker, skill-seekers, trinitycore-335, golang, nodejs, rust,
  java-openjdk, webmin, adguard-home, monica-crm) gegenüber dem kleineren
  SPEC-Katalog (SPEC.md:1129-1138). Drift Catalog ↔ SPEC.
- **Keine Tests** für Extensions-Routen/Streamer/Status gefunden.

### Gemeinsam
- **Verwechslungs-Risiko Plugin/Extension** dokumentarisch nicht im Code
  abgegrenzt (gleiche UI-Vokabeln, getrennte Subsysteme). Beide Admin-only,
  beide mit Install/Uninstall, aber semantisch komplett verschieden.
