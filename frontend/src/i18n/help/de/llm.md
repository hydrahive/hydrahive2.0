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

### Anthropic mit Claude-Abo (Pro/Max) einrichten — OAuth-Token

Mit einem Claude-Abo (Pro/Max) kannst du deinen Account statt eines
kostenpflichtigen API-Keys nutzen. Der OAuth-Token wird **in der Shell mit der
Claude-Code-CLI erzeugt** und hier ins normale API-Key-Feld eingefügt — HydraHive
erkennt am Präfix `sk-ant-oat...` automatisch, dass es ein OAuth-Token ist.

1. In einer Shell mit installierter Claude-Code-CLI den Befehl ausführen:
   ```
   claude setup-token
   ```
2. Es öffnet sich der Browser → mit deinem Claude-Account (Pro/Max) **anmelden
   und autorisieren**.
3. Danach erscheint **in der Shell** ein langlebiger Token (`sk-ant-oat01-...`,
   ~1 Jahr gültig). Diesen kopieren.
4. Hier **Provider hinzufügen** → **Anthropic**.
5. API-Key-Feld: den kopierten `sk-ant-oat01-...`-Token einfügen (kein
   OAuth-Login-Button nötig — der wird nur für ChatGPT/Codex gebraucht).
6. Modelle ankreuzen (z.B. `claude-sonnet-4-6`, `claude-opus-4-8`).
7. **Hinzufügen**.
8. Standard-Modell setzen, **Verbindung testen** klicken — sollte "OK" zurückgeben.

> Alternativ geht auch ein klassischer API-Key aus der Anthropic-Console
> (`sk-ant-api03-...`) — dann wird pro Nutzung nach API-Preisen abgerechnet statt
> übers Abo.

### ChatGPT Plus/Pro (Codex) per OAuth-Login

Das ist der **einzige** Provider mit echtem OAuth-Login-Button in der GUI (kein
Key nötig):

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
