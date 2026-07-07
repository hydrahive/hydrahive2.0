# LLM-Konfiguration

## Was ist das?

Hier registrierst du **Sprachmodell-Provider** mit deren API-Keys. HydraHive2 unterstützt mehrere Provider parallel — du kannst Anthropic, MiniMax, OpenAI und andere gleichzeitig konfigurieren und pro Agent entscheiden welches Modell genutzt wird.

Das **Standard-Modell** wird verwendet wenn ein Agent kein eigenes Modell explizit angibt.

## Was kann ich hier tun?

- **Provider hinzufügen** — Auswahl aus 7 vorkonfigurierten + Custom
- **API-Keys verwalten** (verschlüsselt nirgends, bleiben in der Config-Datei `~/.hh2-dev/config/llm.json`)
- **Modelle pro Provider auswählen** über klickbare Pills
- **Standard-Modell setzen** — Dropdown aus allen verfügbaren Modellen
- **Verbindung testen** — sendet eine Test-Anfrage `"Reply with exactly one word: OK"`
- **Provider entfernen** über das Mülleimer-Icon

## Wichtige Begriffe

- **Provider** — der Anbieter (Anthropic, OpenAI, MiniMax, Groq, Mistral, Gemini, OpenRouter)
- **API-Key / Token** — Zugangsdaten. Format unterscheidet sich:
  - Anthropic: `sk-ant-api03-...` (klassisch) oder `sk-ant-oat01-...` (Claude-Max-OAuth)
  - OpenAI: `sk-...`
  - MiniMax: JWT-Token (`eyJ...`)
  - Gemini: `AIza...`
- **Standard-Modell** — Default für Agents ohne eigenes Modell
- **Context-Window** — Token-Größe die das Modell überhaupt sehen kann (wichtig für Compaction-Schwelle)

## Schritt-für-Schritt

### Anthropic einrichten — drei Wege

Für Anthropic gibt es **drei** Wege. Alle enden im selben Provider „Anthropic".
Wenn du sowohl einen Key als auch OAuth hinterlegst, hat **OAuth Vorrang**.

**Weg 1 — klassischer API-Key (Pay-per-Use)**
1. In der Anthropic-Console einen API-Key erstellen (`sk-ant-api03-...`).
2. **Provider hinzufügen** → **Anthropic** → Key ins **API-Key-Feld** einfügen.
3. Modelle ankreuzen, **Hinzufügen**, **Verbindung testen**.
   Abrechnung nach API-Preisen (nicht übers Abo).

**Weg 2 — Abo-Token per CLI (`claude setup-token`)**
Nutzt dein Claude-Abo (Pro/Max) statt API-Credits. Der Token wird **in der Shell
mit der Claude-Code-CLI** erzeugt und ins API-Key-Feld eingefügt — HydraHive
erkennt am Präfix `sk-ant-oat...` automatisch, dass es ein OAuth-Token ist.
1. In einer Shell mit Claude-Code-CLI: `claude setup-token` ausführen.
2. Browser öffnet sich → mit Claude-Account **anmelden und autorisieren**.
3. Der langlebige Token (`sk-ant-oat01-...`, ~1 Jahr) erscheint **in der Shell** →
   kopieren.
4. **Provider hinzufügen** → **Anthropic** → Token ins **API-Key-Feld** einfügen.
5. Modelle ankreuzen, **Hinzufügen**, **Verbindung testen**.

**Weg 3 — OAuth-Login per Klick (Abo, ohne CLI)**
Der bequemste Weg mit Claude-Abo — kein Terminal nötig. HydraHive holt den Token
selbst und **erneuert ihn automatisch** (Auto-Refresh), du musst dich also nicht
alle paar Tage neu einloggen.
1. **Provider hinzufügen** → **Anthropic**.
2. Unter dem API-Key-Feld beim OAuth-Login **Login öffnen** klicken → im Browser
   bei **claude.ai** anmelden und autorisieren.
3. Der Browser leitet auf `localhost:53692` um und zeigt „Seite nicht erreichbar" —
   **das ist normal**. Die ganze URL aus dem Adressfeld kopieren.
4. URL im zweiten Schritt einfügen → **Verbinden**. Es erscheint „Per OAuth
   verbunden".
5. Modelle ankreuzen, **Hinzufügen**, Standard-Modell setzen, **Verbindung testen**.

> Das API-Key-Feld bleibt bei allen drei Wegen sichtbar — der OAuth-Login (Weg 3)
> ist eine zusätzliche Option, kein Ersatz.

### ChatGPT Plus/Pro (Codex) per OAuth-Login

Auch ChatGPT hat einen OAuth-Login-Button (kein Key nötig):

1. **Provider hinzufügen** → **ChatGPT Plus/Pro (Codex)**.
2. **Login öffnen** klicken → im Browser bei ChatGPT anmelden.
3. Der Browser leitet auf `localhost:1455` um und zeigt „Seite nicht erreichbar" —
   **das ist normal**. Die ganze URL aus dem Adressfeld kopieren.
4. URL im zweiten Schritt einfügen → **Verbinden**.

### MiniMax-Provider mit Token-Plan

1. **Provider hinzufügen** → **MiniMax**
2. API-Key: dein JWT-Token (`eyJ...`)
3. Modelle: `MiniMax-M2.7` ankreuzen
4. **Hinzufügen**
5. **Verbindung testen**

### Mehrere Provider parallel

Du kannst alle relevanten Provider gleichzeitig haben. Beim Anlegen eines Agents wählst du dann das gewünschte Modell aus dem Pool aller verfügbaren.

## Typische Fehler

- **`OAuth authentication is currently not supported`** — passiert wenn LiteLLM den OAuth-Token als Bearer schickt. HydraHive2 umgeht das durch direkte Anthropic-SDK-Nutzung — bei diesem Fehler bitte Backend-Log prüfen.
- **`Error code: 429 - rate_limit`** — du bist über deinem Token-Limit. Warten oder anderen Provider nutzen.
- **`Error code: 401`** — falscher API-Key. Token kopieren ohne Whitespace.
- **`LLM Provider NOT provided`** (LiteLLM-Error) — passiert wenn ein Modell-Name nicht erkannt wird. Lösung: das Modell im Frontend-Dropdown auswählen statt manuell tippen.

## Tipps

- **Vorgeschlagene Modelle nutzen** statt selbst zu tippen — verhindert Tippfehler bei Modell-Namen
- **Für sensible Daten**: lokale Modelle via Ollama (mit OpenAI-kompatiblem Endpoint) als Custom-Provider eintragen
- **Cost-Awareness**: Sonnet-4-6 ist teurer als Haiku — pro Aufgabe das passende Modell wählen
- **Token-Plan-Abo (Claude Max)** statt Pay-per-Use spart bei intensiver Nutzung deutlich
