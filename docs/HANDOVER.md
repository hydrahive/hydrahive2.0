# HydraHive2 — Übergabe (Stand 2026-05-02 früh)

Konsolidierter Snapshot. Beim Wieder-Aufnehmen diese Datei zuerst,
dann SPEC.md, dann konkret nach offenen Tasks fragen.

## Heute geschafft (~30 Commits)

### Audit + Issues geschlossen (17 Stück)

Großes Aufräumen — viele Features waren schon umgesetzt aber Issues offen:
- **#42** Kosten pro Bubble (USD), **#43** Edit+Resend, **#46** Retry-Button,
  **#49** System-Prompt-Tooltip, **#53** Drag-Drop Bilder, **#54** Compact-
  Imminent-Warning, **#61** Git Commit/Push/Pull aus UI, **#67** paused-Lifecycle,
  **#85** AgentForm Sticky-Save-Bar, **#86** Tailscale-Card mit Peers,
  **#87** AgentLink-Card mit Telemetry, **#88** 5 Theme-Farben, **#92** MiniMax
  via Anthropic-SDK, **#93** MiniMax-Creator-Plugin, **#94** Console-Cleanup,
  **#97** Bridge-Setup-Knopf, **#98** Beliebiger Repo-Pfad
- **#12** DevLauncher → Tool-Confirm-System (SPEC umgeschrieben mit Tills OK)
- **#33** Process-Meta — sequenziell-arbeiten ist Praxis

### Bugfixes
- **`fix(vms): cpu=qemu64 statt cpu=max`** — FreeBSD-VMs crashten in TCG-
  Containern bei AES-NI-Emulation. 218 ist LXC-Container ohne /dev/kvm,
  jetzt fällt qemu sauber auf qemu64 zurück.
- **`fix(systemd): KillMode=process`** — VMs überleben jetzt Backend-Updates.
- **`fix(installer): sshpass-Check in update.sh`** — alte Installs ziehen
  sshpass nach.
- **`fix(_minimax_usage)`**: `load` → `load_config` — Backend-Crash-Loop
  nach Push, manuell mit `sudo -u hydrahive git pull && systemctl restart`
  rausgeholt. **Lesson:** vor Push immer Backend-Imports smoke-testen.

### Tool-Confirm-System (#12 alternativ)
Statt OS-Sandbox: per-Agent-Toggle `require_tool_confirm`. Wenn an, sieht
User vor jedem Tool-Call ein Banner mit Erlauben/Verweigern. Auto-deny
nach 5 Min Timeout.
- `core/src/hydrahive/runner/tool_confirmation.py` — Pending-Store mit
  asyncio.Future
- Frontend: `chat/ToolConfirmBanner.tsx` über Input
- SPEC.md angepasst (mit Tills explizitem OK) — keine OS-User-Isolation
  mehr, Sicherheit via User-Auth + Tool-Permission-Prompts

**Memory-Eintrag:** `feedback_agents_full_tool_access.md` —
"HydraHive-Agents arbeiten wie Claude Code + OpenClaw" — voller Tool-
Zugriff, keine Sandbox-Whitelists, kein "darf ich nicht"-Pattern.

### Buddy-Page (neu)
**Kompletter neuer Bereich** unter `frontend/src/features/buddy/` +
`core/src/hydrahive/buddy/`:

- `/` zeigt jetzt eine **Buddy-Page** statt Dashboard. Dashboard ist auf
  `/dashboard`, alter Chat auf `/devchat` (Bookmarks redirected).
- **Auto-Buddy-Create**: pro User ein Master-Agent mit `is_buddy=True`,
  Lifetime-Session, gewürfelter Charakter aus 31 Universen × 5-10
  konkreten Charakter-Namen.
- **TV-Look-UI**: zentrale Box mit Top-Bezel + Bottom-Bezel + Power-LED + Stand
- **Eigene Bubble-Komponenten** (`BuddyBubble.tsx`, `BuddyMessageList.tsx`)
  ohne Tokens/Iteration/Stop-Reason. User-Bubble in amber-Pill-Style
  (wie Bridge-Card im Dashboard), Buddy-Bubble in emerald-Pill-Style.
- **Tool-Aufrufe komplett ausgeblendet** — nur Text + Bilder + Audio
- **Charakter-Bootstrap**: bei erstem Kontakt würfelt Backend Universum
  + 3-5 konkrete Charakter-Kandidaten. LLM wählt einen aus, speichert
  im Memory unter Key 'character', bleibt in der Rolle.
- **Anti-Gandalf-Bias**: Pool ohne Mainstream-Default-Charaktere — keine
  Gandalfs/Yodas/Sherlocks mehr, sondern z.B. Kapitän Haddock,
  Marvin der depressive Roboter, Granny Weatherwax.

### Media-Player für Chat
- `MediaPreview.tsx` — extrahiert Bild/Audio/Video-URLs aus Text
- HTTP(S)-URLs + absolute Paths (`/tmp/foo.png`, `/var/lib/hydrahive2/...`)
- Backend `GET /api/files?path=...` mit Pfad-Allowlist + Path-Traversal-
  Schutz liefert `/tmp` und `/var/lib/hydrahive2` aus
- Frontend rewriten absolute Paths zu `/api/files?path=<encoded>`
- Funktioniert in DevChat (ToolResultCard) + Buddy (BuddyBubble)

### Theme-System (#88)
- 5 Themes (violet/cool/warm/forest/mono) via CSS-Variablen am `<html>`
- ThemeSwitcher in ProfilePage, localStorage-persistent
- Brand-Stellen migriert: Logo, Login, Avatar, Modals, AgentForm, Chat,
  Scrollbars

### Dashboard-Cockpit
- HealthStrip (1-Liner)
- Stats kompakter (4 Tiles, kleinerer Padding)
- Tailscale | AgentLink (beide ausführlich mit Peers/Specialists)
- Recent Sessions | Active Agents (50:50, Agents nicht mehr full-width)
- Servers als Grid 2-4 Spalten, kein 8-Cap
- MiniMax-Quota-Card (token_plan/remains aus altem HH portiert)

## Offene Themen

- **Buddy-Spielereien**: Tamagotchi-Charakter (Rive/Live2D/VRM —
  Beholder/Sasquatch waren beide nichts, asset-Suche muss weiter), Online-
  Radio im Header, Achievement-Toasts, Wetter-Pille, Pomodoro-Timer
- **Profil-Toggle**: chat-quick vs dashboard als Default-Landing-Page
- **#28** Datei-Größen >150: 24 Backend + 20 Frontend Files noch über
- **Andere Provider-Quotas**: Anthropic-Rate-Limit-Header für Quota-Anzeige
- **Bestehende Buddies** (vor Charakter-Bootstrap): haben eigenen
  system_prompt.md, der neue Soul-Code wirkt nur bei NEU erstellten —
  alte können manuell überschrieben oder gelöscht und neu angelegt werden

## Test-Server-Stände

- **218** (chucky@hh2-218 / lummerland123) — LXC-Container auf TrueNAS,
  kein /dev/kvm. Stand: nicht aktuell, braucht Update-Trigger
- **Tills Produktiv** (separater Server, nicht 218) — Update-Trigger
  via `sudo touch /var/lib/hydrahive2/.update_request`

## Lessons Learned heute

- **Vor Push: Backend-Imports smoke-testen** — `_minimax_usage`-Import
  hieß `load` statt `load_config`, ganzer Service crash-loop. Seitdem:
  `.venv/bin/python -c "from hydrahive.api.main import app"` als
  Quick-Check vor jedem Push.
- **`git add -A` ist riskant** — heute mal versehentlich `image_001.jpg`
  mit committed. Cleanup-Commit. Sollte expliziter werden.
- **LLM-Bias auf Default-Charaktere** ist hart — Soft-Avoid-Constraints
  reichen nicht (Gandalf trotz "Vermeide: Gandalf"). Lösung: Backend
  würfelt KONKRETE Kandidaten vor, LLM wählt nur aus Allowlist.
- **Asset-Pipeline für Tamagotchi**: Rive ist nicht plug-and-play —
  Beholder hatte zu wenig States, Sasquatch lief gar nicht. Live2D
  oder VRM wären robuster, brauchen aber eigene Lib + Modelle.
