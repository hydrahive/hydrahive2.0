# HydraHive2 — Übergabe (Stand 2026-05-05 abend)

Konsolidierter Snapshot. Beim Wieder-Aufnehmen diese Datei zuerst,
dann SPEC.md, dann konkret nach offenen Tasks fragen.

---

## Was heute (5. Mai 2026) erledigt wurde

### Installer-Umbau — Pre-Flight-Wizard
- 9 Komponenten optional auswählbar (Tailscale, Postgres, Voice, Containers,
  VMs, AgentLink, Nginx, Samba, WhatsApp). Auswahl wird in
  `/etc/hydrahive2/install.conf` gespeichert. Re-Run überspringt Fragen.
- Phase 10b ergänzt: 55-voice.sh wird jetzt vom install.sh aufgerufen
  (vorher fehlte das im Frisch-Install).
- Module-Header-Skip-Checks bei allen 9 optionalen Modulen + update.sh lädt
  install.conf.
- Tag `milestone-installer-pre-wizard` (1fe3558) zum Zurückrollen.
- curl-Bootstrap: frische Ubuntu-VMs haben kein curl, Installer holt's vor
  NodeSource/uv-Setup.
- git safe.directory + chown hydrahive auf llm.json/install.conf — sonst
  killen Web-UI-Saves still und sudo git pull bricht ab.
- Installer-Übersicht am Ende: drei Blöcke (Login / System / Komponenten),
  übersprungene kompakt unten mit `--reconfigure`-Hinweis.

### LLM-Provider-Wizard im Installer (analog OpenClaw)
- `installer/lib/llm-wizard.sh` fragt nach allen 8 Providern, schreibt
  `llm.json` mit chmod 640 hydrahive:hydrahive (Backend muss schreiben können).
- Sonnet als Default-Modell statt Opus.
- LLM-Modell-Strings mit Provider-Prefix für LiteLLM-Routing
  (`openai/`, `nvidia_nim/`, `groq/`, `mistral/`, `gemini/`, `openrouter/`).
- Anthropic + MiniMax laufen direkt über Anthropic-SDK, brauchen keinen Prefix.
- Wizard löscht keine bestehenden Provider beim --reconfigure mehr.
- Pipe/Heredoc-Bug gefixt (Python liest jetzt korrekt von stdin).

### Anthropic OAuth (vollständig fertig)
- PKCE-Flow mit `code=true` + `state=verifier` (pi-mono-Quirk).
- Lokaler HTTP-Server auf 127.0.0.1:53692 + manueller Code-Paste-Fallback
  (für Remote-SSH ohne Tunnel).
- Cloudflare-UA-Header gesetzt damit platform.claude.com nicht 403 wirft.
- `oauth/anthropic.py:resolve_anthropic_token()` refresht Token automatisch
  vor Ablauf, Backend-LLM-Pfade nutzen das.
- Funktioniert komplett: Wizard fragt "OAuth ja/nein", User klickt URL,
  Callback kommt automatisch, Token + Auto-Refresh laufen.

### Tool-Loop für LiteLLM-Provider (NVIDIA, OpenAI, Groq, Mistral, Gemini, OpenRouter)
- `runner/_litellm_convert.py`: Konverter Anthropic ↔ OpenAI-Format
  (Messages, Tools, Response, stop_reason).
- `runner/_llm_bridge_backends.litellm_call()`: ruft `litellm.acompletion`
  mit `tools=[...]`, konvertiert Antwort. 120s-Timeout.
- `call_with_tools` wirft kein NotImplementedError mehr — alle Provider
  durchgereicht.
- Auto-Retry ohne Tools wenn das Modell Tool-Use nicht unterstützt
  (z.B. qwen2.5-coder, abab5.5).
- Streaming bleibt für non-Anthropic/MiniMax als StreamingNotSupported,
  fallback auf litellm_call (non-streaming).

### Modell-Picker im Chat- und Buddy-Header
- `frontend/src/features/chat/ModelPicker.tsx`: klickbare Pill mit Dropdown.
  Zeigt alle in llm.json gespeicherten + alle bekannten KNOWN_PROVIDERS-
  Modelle der konfigurierten Provider.
- Auswahl setzt `session.metadata.model_override`, runner liest das frisch
  vor jedem LLM-Call. Switch greift mid-session ohne Restart.
- Buddy-Header zeigt denselben Picker.
- Override pro Session, Reset stellt zurück auf Agent-Default.

### LLM-Modell-Catalog (`/llm/catalog`)
- Backend `llm/catalog.py`: holt `/v1/models` live von 6 Providern,
  joint mit interner Metadata-Tabelle (~50 Modelle gepflegt:
  context_window, tool_use, category, family, params).
  Anthropic + MiniMax als Static-Liste.
- API-Routes: GET /api/llm/catalog, POST /api/llm/catalog/test (1 Mini-Call,
  zeigt Latenz + Error), POST /api/llm/catalog/use-in-agent (setzt
  agent.llm_model und ergänzt das Modell automatisch in
  providers[].models, sonst würde validate_model blocken).
- Frontend `CatalogPage.tsx`: Tabs pro Provider, Tabelle (Suche, Filter
  Tools/Ohne/Unbekannt), Test-Button, Use-in-Agent-Dialog.

### NVIDIA NIM
- Frontend `_llm_providers.ts` jetzt mit allen 121 Chat-Modellen vom
  Live-Katalog.
- Context-Window-Lookup: qwen2.5* → 32k, qwen3* → 262k, andere konservativ.
- Buddy mit qwen2.5-coder hat ContextWindowExceeded geschmissen weil
  Lookup falsch war → fixed.

### OpenAI Codex OAuth (Häppchen 1 von 3)
- `oauth/openai_codex.py`: PKCE, authorize_url, exchange_code (form-encoded),
  refresh_access_token, JWT-decode für `chatgpt_account_id`.
- `installer/lib/oauth_codex_cli.py`: Browser-Login + lokaler HTTP-Server
  auf 127.0.0.1:1455 + Manual-Paste-Fallback.
- Wizard fragt bei OpenAI: "OAuth-Login (ChatGPT Plus/Pro via Codex)?".
- **Login funktioniert** — Token landet in llm.json mit account_id.
- **Backend-Call zu chatgpt.com/backend-api/codex/responses fehlt noch**
  (Häppchen 2). LLM-Calls mit OAuth-Token laufen aktuell noch durch
  LiteLLM → 401 weil OAuth-Token nicht für api.openai.com gültig.

### SPEC-Erweiterungen (alle als standalone-Commits)
- `381f7c1`: Chat-Header bekommt Modell- und Effort-Switcher
- `f291b2b`: OAuth-Login für Anthropic / MiniMax / OpenAI Codex
- `42e55d8`: LLM-Modell-Catalog mit Live-Listing + Metadata

### Reasoning-Effort low/medium/high (Backend-Mapping fertig, Frontend pausiert)
- `apply_thinking_budget()` in `_anthropic.py`: low=1k, medium=4k, high=16k
  Tokens. max_tokens automatisch hochgezogen, temperature=1.0 erzwungen.
- Parameter `reasoning_effort` durchgereicht: stream_with_tools →
  call_with_stream_or_fallback → anthropic_stream / minimax_stream.
- 5 Unit-Tests grün.
- **Frontend Effort-Pill pausiert** auf Tills Wunsch — kommt nach OAuth.

---

## Aktuell offen / nächste Schritte

### Direkt anschließend
1. **OpenAI Codex OAuth Häppchen 2** — Backend-Provider `_openai_codex_call`
   gegen chatgpt.com/backend-api/codex/responses (Streaming, Tool-Use,
   Responses-API). Vorlage in `octopos/orchestrator_llm.py:1489+`.
2. **OpenAI Codex OAuth Häppchen 3** — Routing in `runner/llm_bridge.py`
   und `client.py`: wenn openai-Provider OAuth-Block hat, codex_call statt
   litellm.

### Effort-Pill im Chat-Header (pausiert)
- Backend-Mapping fertig, Frontend fehlt:
  - ModelPicker-ähnliche Pill für low/medium/high
  - Persistenz in session.metadata.reasoning_effort
  - runner.run() Signatur erweitern + API-Schema-Erweiterung

### MiniMax OAuth (Device-Code-Flow) — pausiert
- API-Key reicht aktuell, OAuth nicht prio.

### Backlog (keine Reihenfolge)
- Telegram + Matrix-Adapter
- Branching/Tree-View in Chat
- Bundle-Splitting (#95)
- DB-Indizes (#96)
- AgentLink HTTPS Mixed-Content (#90)
- MCP-Datamining-Server deployen + als Tool einbinden
- Buddy-Spielereien (Tamagotchi-Animation, Online-Radio)
- Mehr NVIDIA-Modelle in der Metadata-Tabelle pflegen (aktuell ~25 von 121
  bekannt, Rest als "unbekannt" mit ?-Badge)

---

## Installer / Server

### Test-Server 218 (chucky@hh2-218 / 192.168.178.218)
- LXC-Container auf TrueNAS, kein /dev/kvm
- Repo: `/opt/hydrahive2`, Service-User: `hydrahive`
- **Stand**: aktuell, Tag `014f7c9`
- Update-Trigger: `sudo touch /var/lib/hydrahive2/.update_request`
- PostgreSQL läuft, DSN in `/etc/hydrahive2/pg_mirror.dsn`
- Buddy-Agent läuft mit nvidia_nim/qwen3-coder-480b-a35b-instruct

### Frischer Test-Server (192.168.178.179, till@till-b450nh)
- Mehrfach heute neu installiert, läuft jetzt sauber
- Kunde will nachher selber installieren — keine bekannten Issues mehr

### Installer-Reihenfolge (modules/) — aktuell
```
00-deps  (curl-bootstrap, NodeSource, uv, gh, mmx)
10-user  20-paths
30-python  40-frontend
45-whatsapp  47-samba  48-postgres
50-systemd  60-nginx
65-vms  70-containers  55-voice  75-agentlink  80-tailscale
+ LLM-Provider-Wizard (lib/llm-wizard.sh)
```

---

## Wichtige Lektionen aus dieser Session

- **Quick-Fix-first ist verboten** (siehe Memory `feedback_no_quick_fixes.md`):
  Tills neue Hauptregel — immer saubere Lösung, Quick-Fix nur in echten
  Notfällen die Till explizit benennt.
- **llm.json-Permissions** sind kritisch: muss hydrahive:hydrahive 640 sein,
  sonst sieht Web-UI-Save success aus, persistiert aber nicht.
- **Provider-Prefix für LiteLLM**: alle Modelle außer Anthropic/MiniMax
  brauchen den Provider-Prefix (nvidia_nim/, openai/, etc.) sonst routet
  LiteLLM falsch.
- **Tool-Use ist nicht universal**: NVIDIA NIM hat einige Modelle die
  kein Function-Calling können (qwen2.5-coder, codestral) — Auto-Retry
  ohne tools fängt das ab.
- **Cloudflare blockt Default-Python-User-Agent** an Anthropic/OpenAI:
  Claude-Code-/Codex-UA setzen damit nicht als Bot erkannt wird.
- **Browser-Cache**: bei Frontend-Änderungen oft Strg+Shift+R nötig,
  Strg+F5 reicht nicht immer.
- **OpenAI Codex JWT-Decode**: account_id muss aus dem access_token
  extrahiert werden (Custom-Claim `https://api.openai.com/auth.chatgpt_account_id`)
  — das ist kein Standard-OAuth.
- **HH2-Tool-Loop unterstützte vorher nur Anthropic + MiniMax**
  (NotImplementedError für alle anderen). Heute auf alle LiteLLM-Provider
  erweitert.

---

## Code-Map (neue/geänderte Dateien heute)

### Installer
```
installer/install.sh                          erweitert (Wizard, Übersicht)
installer/update.sh                           install.conf laden + safe.directory
installer/onboard.sh                          NEU (standalone wizard-Aufruf)
installer/lib/llm-wizard.sh                   NEU (Provider-Wizard)
installer/lib/oauth_anthropic_cli.py          NEU (OAuth-Flow Anthropic)
installer/lib/oauth_codex_cli.py              NEU (OAuth-Flow OpenAI Codex)
installer/modules/00-deps.sh                  curl-bootstrap, gh-cli
installer/modules/30-python.sh                git safe.directory
installer/modules/45..80-*.sh                 Header-Skip-Checks
```

### Backend
```
core/src/hydrahive/oauth/anthropic.py         NEU
core/src/hydrahive/oauth/openai_codex.py      NEU
core/src/hydrahive/llm/_anthropic.py          + extended_thinking budget
core/src/hydrahive/llm/client.py              resolve_anthropic_token-Pfad
core/src/hydrahive/llm/catalog.py             NEU (Live-Listing + Metadata)
core/src/hydrahive/runner/_litellm_convert.py NEU (Anthropic↔OpenAI Konverter)
core/src/hydrahive/runner/_llm_bridge_backends.py +litellm_call
core/src/hydrahive/runner/llm_bridge.py       LiteLLM-Routing für non-Claude
core/src/hydrahive/runner/llm_bridge_stream.py  reasoning_effort durchreichen
core/src/hydrahive/runner/_stream_providers.py  reasoning_effort durchreichen
core/src/hydrahive/runner/_call.py            reasoning_effort durchreichen
core/src/hydrahive/runner/runner.py           model_override aus session.metadata
core/src/hydrahive/db/sessions.py             set_model_override()
core/src/hydrahive/api/routes/sessions.py     model_override-Update
core/src/hydrahive/api/routes/_sessions_helpers.py  SessionUpdate +model_override
core/src/hydrahive/api/routes/llm_catalog.py  NEU
core/src/hydrahive/compaction/tokens.py       qwen-Window differenzieren
```

### Frontend
```
frontend/src/features/chat/ModelPicker.tsx    NEU
frontend/src/features/chat/_ChatHeader.tsx    Pill statt static
frontend/src/features/chat/ChatPage.tsx       onSessionChanged
frontend/src/features/chat/api.ts             updateSession +model_override
frontend/src/features/buddy/BuddyPage.tsx     ModelPicker im Buddy-Header
frontend/src/features/llm/CatalogPage.tsx     NEU
frontend/src/features/llm/_llm_providers.ts   121 NVIDIA-Modelle, Prefix für alle
frontend/src/features/llm/api.ts              catalogApi
frontend/src/features/llm/LlmPage.tsx         Catalog-Link
frontend/src/App.tsx                          /llm/catalog Route
```
