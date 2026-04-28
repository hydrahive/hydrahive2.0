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

### Anthropic-OAuth-Token (Claude Max) einrichten

1. Auf https://claude.ai/settings/billing dein Token-Plan-Abo bestätigen
2. OAuth-Token besorgen (siehe Anthropic-Docs)
3. Hier **Provider hinzufügen** → **Anthropic**
4. API-Key-Feld: `sk-ant-oat01-...` einfügen
5. Modelle ankreuzen (`claude-sonnet-4-6` etc.)
6. **Hinzufügen**
7. Standard-Modell setzen, **Verbindung testen** klicken — sollte "OK" zurückgeben

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
