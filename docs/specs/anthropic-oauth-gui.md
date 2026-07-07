# Spec: Anthropic-OAuth-Login in der GUI freischalten (dritter Weg)

## Was

Anthropic bekommt einen dritten Einrichtungsweg: **OAuth-Login per Button**
(anklicken → auf claude.ai bestätigen → Redirect-URL zurückkopieren → verbunden).
Der Token wird automatisch refresht. Die zwei bestehenden Wege bleiben **komplett
unangetastet**:
- Weg 1: klassischer API-Key `sk-ant-api03-...` ins Key-Feld
- Weg 2: `claude setup-token`-Token `sk-ant-oat01-...` ins Key-Feld
- Weg 3 (NEU): OAuth-Login-Button

## Warum

Der komplette Anthropic-OAuth-Code existiert bereits (`oauth/anthropic.py`:
authorize_url / exchange_code / refresh_access_token; `resolve_anthropic_token`
bevorzugt OAuth vor API-Key), ist aber nicht an GUI/Route angeschlossen — die
OAuth-Route lässt nur `openai-codex` durch. Nutzer mit Claude-Abo wollen den
bequemen Klick-Flow ohne CLI.

## Kernentscheidung: hybrider Provider (additiv)

Codex ist rein-OAuth (`auth: "oauth"` → Key-Feld verschwindet). Für Anthropic
darf das NICHT übernommen werden, sonst brechen Weg 1+2. Stattdessen ein NEUES,
additives Flag `oauthOptional: true`:
- Key-Feld bleibt sichtbar + funktionsfähig (Weg 1+2 unverändert)
- zusätzlich darunter ein optionaler OAuth-Login (Weg 3)
- Das bestehende `auth: "oauth"` (erzwingt Key-Feld weg) bleibt exklusiv bei Codex

Konflikt-Priorität: **OAuth vor API-Key** (bestehende `resolve_anthropic_token`-
Logik, unverändert). Hat ein User beides, gewinnt OAuth.

## Wie

### Backend `api/routes/llm_oauth.py`
- Provider-Dispatch statt hartem `== "openai-codex"`:
  - `_provider_module(provider)` → `openai_codex` | `anthropic` (sonst 400).
  - `_default_models(provider)` → Codex-Liste | Anthropic-Liste.
- `oauth_start`: unterstützt `openai-codex` UND `anthropic`. Für Anthropic:
  `anthropic.make_pkce()/make_state()/authorize_url()`.
- `oauth_exchange`: Provider-abhängiger `exchange_code`. Für Anthropic KEIN
  `extract_account_id` (nicht vorhanden) → account_id "".
  **Wichtig:** `_write_provider_oauth` darf ein vorhandenes `api_key` NICHT
  löschen (Koexistenz Weg 1/2 + Weg 3). Nur den `oauth`-Block setzen + ggf.
  Default-Modelle ergänzen, wenn der Provider noch keine hat.
- `oauth_revoke`: auch für `anthropic` (entfernt nur den oauth-Block, api_key
  bleibt).
- Codex-Pfad bleibt funktional identisch.

### Backend `oauth/anthropic.py`
- `make_pkce`/`make_state` sind schon aus `_base` importiert — re-exportieren
  falls nötig (Codex tut das über `# noqa: F401`). Kein Verhaltensänderung.

### Frontend
- `_llm_providers.ts`: Anthropic-Eintrag um `oauthOptional: true` erweitern
  (Key-Placeholder `sk-ant-...` bleibt).
- `ProviderForm.tsx`: neue Bedingung `isOAuthOptional`. Wenn gesetzt:
  Key-Feld normal rendern (wie bisher) UND darunter `OAuthFlow` anzeigen
  (unabhängig vom Key). `isOAuth` (Codex) unberührt. Submit bleibt möglich mit
  Key ODER Token.
- `OAuthFlow.tsx`: provider-spezifische Texte (aktuell hart „OpenAI/ChatGPT",
  „localhost:1455"). Kleine Map je providerId:
  - openai-codex: ChatGPT, localhost:1455/auth/callback
  - anthropic: claude.ai, localhost:53692/callback
  Logik/Flow identisch (start → open → paste URL → exchange).

### Anleitung `i18n/help/{de,en}/llm.md`
- Dritter Abschnitt „Weg 3: OAuth-Login (Claude-Abo, ein Klick)".
- Klar abgegrenzt von Weg 1 (API-Key) + Weg 2 (setup-token).
- Hinweis: Token wird automatisch refresht (löst das „nach 1-2 Tagen tot"-Problem
  früherer Setups).

## Akzeptanzkriterien
- [ ] Anthropic zeigt weiterhin ein API-Key-Feld (Weg 1+2 funktionieren unverändert).
- [ ] Anthropic zeigt zusätzlich einen OAuth-Login (Weg 3): Login öffnen →
      claude.ai bestätigen → URL zurück → verbunden.
- [ ] Nach OAuth-Connect steht ein `oauth`-Block unter Provider `anthropic`,
      ein evtl. vorhandener `api_key` bleibt erhalten.
- [ ] Revoke entfernt nur den oauth-Block.
- [ ] Codex-Flow unverändert.
- [ ] Backend-Tests für den Anthropic-Zweig (start/exchange-Guard, Koexistenz
      key+oauth). pytest + ruff grün. tsc grün.

## Nicht in Scope
- Kein Auto-Login ohne User-Klick.
- Keine Änderung an `resolve_anthropic_token` (OAuth-vor-Key bleibt).
- Kein lokaler Callback-Server (manueller URL-Paste wie bei Codex).
