# HydraHive2 — Übergabe (Stand 2026-04-30 spät, Voice E2E + Butler + Issue-Wellen)

Konsolidierter Snapshot. Beim Wieder-Aufnehmen diese Datei zuerst,
dann SPEC.md, dann konkret nach offenen Tasks fragen.

## TL;DR

Heute durchgezogen, alles live auf 218 (`192.168.178.218`):

1. **LXC-Container Phase 1+2+3** komplett — Lifecycle (incus), Browser-Console
   (xterm.js + WebSocket gegen `incus exec`), Detail-Page mit Tabs
   (Console/Logs/Stats/Konfig).
2. **Butler-Flow-Builder** in 4 Phasen (Datenmodell+Persistenz, Executor+Subtypes,
   ReactFlow-UI vom alten octopos 1:1 übernommen mit Adapter-Schicht,
   WhatsApp-Hook). Master-Agent kann jetzt durch Butler-Regeln umgeleitet werden,
   `respond_as_voice` + `agent_reply_with_prefix` funktionieren.
3. **Google-Style-Layout** statt Sidebar — Top-Bar (Logo + Page-Title + Bento +
   Avatar) und Footer schmal, Hauptbereich nimmt alles, mobile-tauglich.
4. **Hilfe-Seite** `/help` mit Topics-Sidebar und Markdown-Inhalt aus den
   bestehenden i18n-Help-Files.
5. **WhatsApp-Auto-Reconnect** — gepairte User bleiben nach Backend-Restart
   automatisch verbunden.
6. **Voice E2E** — Eingang (STT via Wyoming-faster-whisper als incus-LXC) und
   Ausgang (TTS via mmx-CLI mit Voice-Note inkl. Welle und Sekunden). Voice-
   Mode-System-Hinweis schützt den Master vor Eigen-mmx-Calls,
   `_looks_like_metadata`-Heuristik fängt Datei-Meta-Antworten ab.
7. **Issue-Wellen** P0+P1+P2+P3 komplett durchgearbeitet (~25 Issues),
   inklusive SPEC-Workflow-Guard (#34) als Pre-Commit-Hook + GitHub-Action.
8. **Anthropic-Bypass-Konsolidierung** (#16): Claude-Modelle gehen jetzt komplett
   via anthropic-SDK direkt (OAuth + Bearer einheitlich), LiteLLM bleibt für die
   anderen 6 Provider. Volle Anthropic-Features (Prompt-Caching, Extended
   Thinking, Tool-Streaming) sind dadurch überall verfügbar.

## Was steht (alles getestet, live auf 218)

| Bereich | Stand |
|---|---|
| Backend-Runner | Tool-Loop, Streaming, Loop-Detection, Heal für orphan tool_uses, LLM-Failover, runner.run() mit `extra_system`-Param |
| DB-Layer | sessions/messages/tool_calls/state/vms/vm_snapshots/vm_import_jobs/containers, append-only-Compaction |
| Core-Tools (13) | shell, file_*, dir_list, web_search, http_request, *_memory, todo, send_mail; ask_agent NUR wenn AgentLink konfiguriert (#13) |
| Agents | 3 Typen, CRUD, Pro-User-Isolation, fallback_models, _LazyDefaultTools filtert ask_agent |
| Projekte | Members, Project-Agent, isolierter Workspace |
| Compaction | append-only, Token-Budget-Walk, Plugin-Hooks |
| Chat | SSE-Streaming, Markdown+GFM, Cancel, Bild-/Datei-Upload mit safe_path-Sanitization (#10) |
| LLM-Provider | **Anthropic + MiniMax direkt via anthropic-SDK** (OAuth + Bearer); LiteLLM für OpenAI/OpenRouter/Groq/Mistral/Gemini/NVIDIA |
| MCP | 3 Transports + Pool + 8 Quick-Add |
| **Voice (komplett)** | STT: incus-LXC `hydrahive2-stt` mit Wyoming-Whisper, proxy-device 10300, Auto-Detect-Sprache. TTS: mmx-CLI als hydrahive-User, Auth aus llm.json, Output OGG/Opus mit waveform+seconds. Voice-Mode-System-Hinweis verhindert Eigen-mmx-Calls. Belt-and-Braces _looks_like_metadata-Heuristik. ffmpeg am Host, mmx-Voices-Dropdown im UI mit allen Sprachen. |
| **WhatsApp** | Bridge mit Promise.all-Parallelisierung, Voice-Eingang (audio_failed-Event statt Silent-Drop), Voice-Ausgang als ptt mit Welle, Filter zweistufig (Sender vor STT), Auto-Reconnect, pino-Logging mit Level-Forwarding |
| **Butler** | Datenmodell+Persistenz+Registry, Executor mit Trace+Cycle-Guard+Dry-Run, 5T/7C/9A registriert, ReactFlow-UI mit Adapter, WhatsApp-Hook in handle_incoming, Reply-Actions (reply_fixed/agent_reply/agent_reply_with_prefix/forward/ignore/queue) |
| **Container** | Phase 1+2+3 — Lifecycle, Browser-Console, Detail-Page mit Tabs |
| **VM-Manager** | Phase 1-5 (QEMU+KVM, Browser-VNC, Snapshots, Import, Live-Stats) |
| Layout | Google-Style — Top-Bar + Bento + Avatar-Menu + Footer, identisch Mobile/Desktop, CollapsibleSidebar default zu |
| Hilfe-Seite | `/help` mit Topics-Sidebar, lädt Markdown-Files aus i18n/help/{de,en}/ |
| Plugin-System | MVP + Hub-UI, minimax-creator-Plugin |
| **SPEC-Guard** | pre-commit-Hook + GitHub-Action blocken Mixed-Commits (SPEC.md/CLAUDE.md + Code im selben Commit). CLAUDE.md Punkt 8 dokumentiert die Regel. Bypass via `BYPASS_SPEC_GUARD=1`. |
| Installer | 9 Phasen, ffmpeg in 00-deps, mmx-CLI in 00-deps, mmx-Auth als $HH_USER in 55-voice.sh, ReadWritePaths-Migration via update.sh, git-hook-Bootstrap via `installer/git-hooks/install-hooks.sh` |

## Was offen ist

### Größere Initiativen (P1, je halber bis ganzer Build-Tag)

1. **Container-Phase 3 (optional)**: System-Container (Voice/STT) im
   `/containers`-Frontend als „system-managed" sichtbar machen — analog zu
   User-Containern. UX-Konsistenz, kein Funktionsdefizit.
2. **VM-Phase 6 (optional)**: VM-Detail-Page mit Tabs analog zu Container.
3. **AgentLink-Hookup** (#13 Polish): `ask_agent` ist jetzt nur registriert wenn
   `HH_AGENTLINK_URL` gesetzt — bei Hookup an die echte AgentLink-API ist das
   Tool sofort live ohne weitere Code-Änderung.
4. **Web → WhatsApp-Send** — Antworten aus Web-UI gehen nicht zurück über WA.
5. **Butler-Subtypes nachziehen** — einige UI-Subtypes haben noch keinen
   Backend-Match (`heartbeat_fired`, `discord_event_received`, `contact_known`,
   `git_branch_is`/`author_is`/`action_is`, `email_*_contains`, `discord_*_is`).
   Save geht durch, Match feuert nicht.
6. **Butler-Stub-Actions verkabeln** — `http_post` läuft echt, aber `send_email`/
   `discord_post`/`git_create_issue`/`git_add_comment` sind noch Stubs.

### Dokumentation-Issues offen (#15, #22, #32 — SPEC ist Tills Domäne)

- **#15 ZH-Locale**: SPEC sagt DE/EN/ZH, Code hat DE/EN — Till entscheidet ob
  ZH gebaut wird oder SPEC angepasst.
- **#22 CSP `unsafe-inline`**: 16 Inline-Style-Stellen identifiziert, sauberer
  Fix wäre Nonce-System (>1 Tag Arbeit). P3, dokumentiert offen.
- **#32 PostgreSQL-Zeile**: SPEC erwähnt PostgreSQL für AgentLink (extern), Code
  referenziert es nicht — Till entscheidet ob SPEC umformuliert wird.

### Kleinere Themen

- i18n Phase 4 — zentrale Glossar/FAQ-Sektion in der Hilfe-Seite.
- MCP Phase 4 — Resources + Prompts.
- LLM-Failover-Polish — 429-Cooldown + Exponential-Backoff.

## Live-Server (218)

- **Host**: `192.168.178.218` (vorher .216, hat sich beim setup-bridge.sh geändert)
- **SSH-Alias**: `hh2-216` und `hh2-218` (beide → `.218`)
- **Setup-User**: `chucky` (Passwort `lummerland123`, sudo-fähig)
- **Service-User**: `hydrahive` (no-login)
- **Repo**: `/opt/hydrahive2/` auf main
- **Daten**: `/var/lib/hydrahive2/` (inkl. `vms/`, `whatsapp/`, `wyoming-Modell-Cache im STT-Container`)
- **Config**: `/etc/hydrahive2/` (TLS, butler/, whatsapp/, llm.json)
- **mmx-Auth**: `/home/hydrahive/.mmx/config.json`
- **Frontend-URL**: `https://192.168.178.218/` (Self-Signed-Cert, Browser-Warnung einmal akzeptieren)
- **Self-Update**: aus UI klicken (Admin) ODER `sudo bash /opt/hydrahive2/installer/update.sh`
- **Admin-Passwort** auf 218: `lummerland123`

## Voice-Stack — wie es funktioniert

```
WhatsApp-Voice-Nachricht
  → Bridge (Node, Baileys) downloadMediaMessage → base64
  → POST /api/communication/whatsapp/incoming mit media_type=audio
  → Backend: ffmpeg mp4/m4a/webm → 16kHz mono PCM
  → TCP zu 127.0.0.1:10300 (incus proxy-device)
  → incus-LXC hydrahive2-stt: Wyoming-Faster-Whisper
  → Transkript zurück
  → handle_incoming(event mit voice_mode=true)
  → Master-Agent mit _VOICE_MODE_SYSTEM_HINT als extra_system
  → Master antwortet als Text (kein Eigen-mmx)
  → _looks_like_metadata-Check (Belt-and-Braces)
  → mmx-CLI synthesize_mp3 (env=MINIMAX_API_KEY aus llm.json)
  → ffmpeg MP3→OGG/Opus 16kHz mono
  → ffprobe für Sekunden, ffmpeg+RMS für 64-Byte-Waveform
  → VoiceClip via send_audio an Bridge
  → Baileys sock.sendMessage({ audio, ptt:true, seconds, waveform })
  → User hört echte Voice-Note mit Welle
```

## Heute identifizierte Fallstricke (Memory: feedback_voice_stack_lessons.md)

Die Voice-Migration hat 7 Bugs nacheinander aufgedeckt:

1. **mmx --output statt --out** in `voice/tts.py` — Web-TTS-Endpoint hatte's
   richtig, Voice-Pfad nicht.
2. **OCI-Pull funktioniert nicht in incus 6.0** (Ubuntu 24.04 Default) — Fallback:
   Custom Ubuntu-LXC mit `pip install wyoming-faster-whisper`.
3. **Migrations-Reihenfolge**: alter Docker-Container muss VOR proxy-device-Add
   stoppen, sonst Port-Konflikt → kurzer Voice-Downtime + Health-Wait + Rollback.
4. **Healthcheck false-positive**: incus-Container `RUNNING` + Port `10300` offen
   schien OK — Port gehörte aber dem alten Docker. Healthcheck verschärfen auf
   proxy-device-Existenz.
5. **ffmpeg fehlt am Host**: war im Docker-Container drin, beim Migrations-LXC
   muss am Host nachinstalliert werden — in `00-deps.sh` als REQUIRED_PACKAGES.
6. **mmx-Auth als root**: Token landete in `/root/.mmx/`, hydrahive-Service liest
   `/home/hydrahive/.mmx/`. Lösung: `sudo -u hydrahive HOME=/home/hydrahive mmx auth login`.
7. **ProtectHome=read-only blockiert mmx-Cache**: `/home/$USER/.mmx` muss in
   `ReadWritePaths` der systemd-Service-Unit. Plus mkdir+chown VOR Service-Restart.

Plus auf der UI-Seite:

8. **PUT-Endpoint und Response-DTO synchron erweitern**: neue Felder im
   `WhatsAppConfig` brauchen sowohl Constructor-Read als auch `_config_dict`-Write.
9. **LLM-Agent macht Eigen-Tool-Calls** wenn er denkt er muss Audio erzeugen.
   Lösung: System-Hint in `extra_system` der explizit "kein eigenes mmx, kein
   Markdown, keine Pfade, max ~80 Wörter" sagt + `_looks_like_metadata` als
   Belt-and-Braces.

## Git-Stand am Ende der Session

```
d4b573e fix(whatsapp/voice): Dropdown-Lesbarkeit + alle MiniMax-Sprachen
aae0687 fix(whatsapp/voice): PUT-Config persistiert respond_as_voice/voice_name/stt_language + Dropdown
ea4494a fix(voice): Voice-Mode-System-Hinweis als separater Block + Metadata-Sanity
a5a42ce fix(voice): mmx-Cache-Pfad + Auth als hydrahive-User
de527c9 fix(voice): MINIMAX_API_KEY für mmx-Subprocess aus llm.json setzen
6286846 fix(voice): ffmpeg am Host als Dependency
0174a44 fix(voice): Healthcheck zusätzlich auf proxy-device-Existenz prüfen
8d5bcbf fix(voice): Migration-Reihenfolge — Docker-STT vor proxy-device-Add stoppen
08e1514 feat(voice): STT von Docker auf incus-LXC umgestellt (#25)
… (vorher: SPEC-Guard, Issue-Wellen P0/P1/P2/P3, ButlerPage-Refactor, …)
```

Working-Tree ist clean. Alle Commits gepusht. 218 läuft auf `d4b573e`.

## Empfohlener nächster Build-Tag

1. **Frauchen testen lassen** — Voice ist End-to-End live, hübsche UI, Butler-
   Regeln können rein.
2. **Butler-Subtypes nachziehen** wenn jemand sie wirklich nutzt (heartbeat_fired,
   discord_*, …) — bisher Stubs auf der Backend-Seite.
3. **Stub-Actions verkabeln** (send_email, discord_post, git_*) wenn Bedarf.
4. **AgentLink-Hookup** als nächster großer Punkt — sobald die externe API steht,
   ist's nur HH_AGENTLINK_URL setzen.

Sonst stable. Heute war ein langer Tag.
