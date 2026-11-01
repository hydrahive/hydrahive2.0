# MiniMax auf den aktuellen Stand bringen (M3.1-Flash, M3)

Stand 01.11.2026 · Task 4065328e · Quelle: platform.minimax.io (Docs, Preise) und echte Aufrufe mit dem Key des Admins
(je ~15 Token). Kein Eingriff in andere Anbieter.

## Befund (gemessen)

- **Live-Liste** `GET https://api.minimax.io/v1/models` (Bearer) liefert 9 Modelle, nur `id/created/owned_by`:
  M3.1-Flash, M3, M2.7, M2.7-highspeed, M2.5, M2.5-highspeed, M2.1, M2.1-highspeed, M2.
- **Echter Aufruf:** M3.1-Flash, M3, M2.7(-highspeed), M2.5(-highspeed) antworten. **M2.1, M2.1-highspeed, M2 → 404
  „no longer available (2069)“**, stehen aber noch in der Liste. `MiniMax-Text-01` antwortet noch, fehlt in der Liste.
  `abab6.5s-chat` gibt es nicht mehr.
- **Unser Stand:** `PROVIDER_ENDPOINTS["minimax"]["url"] = None` („kein Katalog“), Fallback-Liste mit Text-01/M1/abab/embo,
  Metadaten nur für alte Modelle → die Auswahl stimmt nicht.
- **Denken:** M3.1-Flash denkt immer, `thinking: disabled` → 400, Tiefe über `output_config.effort`
  (low/medium/high/xhigh/max, ohne Angabe max). M3 denkt nur mit `thinking: {type: adaptive}`. M2.x denkt immer.
  `temperature`/`top_p` werden ignoriert. Wir senden heute für alle MiniMax-Modelle `thinking: enabled` +
  `budget_tokens` (Legacy) und setzen `temperature=1.0`.
- **Bilder:** Anthropic-`image`-Block (base64) wird von M3.1-Flash und M3 richtig gelesen. `convert_images_for_minimax`
  (Umbau auf `image_url`) ist für M3.x unnötig; M2.7 versteht Bilder gar nicht.
- **Mehrrunden-Werkzeuge:** Rückgabe des `thinking`-Blocks und `cache_control` (system, Werkzeug, 1 h) werden von M3.1-Flash
  und M3 akzeptiert (HTTP 200). Das heutige Entfernen von `cache_control` (`strip_minimax_cache_control`, damals HTTP 500
  bei M2) bleibt unangetastet, bis ein Test es für M3 widerlegt, ist aber kein Teil dieser Etappe.
- **Preise** (USD je Mio. Token, Standard, Seite „Pricing Overview“): M3.1-Flash 0,15 Eingabe / 0,60 Ausgabe / 0,015 Cache
  lesen. M3 bis 512k Eingabe (dauerhaft −50 %): 0,30 / 1,20 / 0,06; darüber 0,60 / 2,40 / 0,12. Priority kostet das 1,5-fache.
  Im Backend (`_pricing.py`) gibt es für MiniMax **keine** Preise → Kosten bleiben leer. Das Frontend kennt nur `minimax-m2`.
  M2.x hat keine veröffentlichten Preise mehr (Frontend-Wert 0,30/1,20 bleibt als Schätzung).
- **Quota** `GET /v1/token_plan/remains`: nur noch ein Eintrag „general“, Zähler 0 (Pay-as-you-go). Die Oberfläche blendet
  Einträge mit Summe 0 schon aus → bleibt richtig.

## Änderungen

1. **Katalog** (`llm/_catalog_data.py`, `llm/catalog.py`):
   - `PROVIDER_ENDPOINTS["minimax"]` = Live-Liste (Bearer).
   - `STATIC_MODELS["minimax"]` = M3.1-Flash, M3, M2.7, M2.7-highspeed, M2.5, M2.5-highspeed.
   - Sperrliste `RETIRED_MODELS["minimax"]` = M2.1, M2.1-highspeed, M2, Text-01, abab* usw.: werden aus Live- und Fallback-Liste
     entfernt, ebenso aus der Nutzer-Modellliste des Providers. Pflegeort ist diese eine Liste.
   - `METADATA`: M3.1-Flash und M3 (Kontext 1 000 000, Werkzeuge, Bild-Eingabe), M2.7/M2.5 (Kontext 200 000, nur Text).
2. **Denk-Stufen** (`llm/_anthropic.py`, `llm/reasoning_effort.py`):
   - M3.1-Flash: `thinking: adaptive` + `output_config.effort` (low…max), nie `disabled`, `temperature` weglassen.
   - M3: ohne Stufe nichts senden; mit Stufe `thinking: adaptive` + `output_config.effort`; `temperature` weglassen.
   - M2.x: unverändert (Legacy-Budget).
   - `effort_levels_for_model` liefert für M3.1-Flash/M3 low…max, für M2.x low/medium/high.
3. **Bilder** (`llm/_anthropic.py`, `llm/client.py`): `convert_images_for_minimax` entfällt für M3.x (Anthropic-Block durchreichen);
   für M2.x bleibt es wie bisher.
4. **Preise** (`llm/_pricing.py`, `frontend/src/features/chat/pricing.ts`): M3.1-Flash und M3 eintragen (Provider `minimax`),
   Frontend-Regeln für M3.x ergänzen. Alte `abab`-Regel raus.
5. **Oberfläche** (`frontend/src/features/llm/_llm_providers.ts`): Platzhalter des Key-Felds stimmt nicht (`eyJ…`, Keys beginnen mit `sk-`).

Nicht Teil dieser Etappe: Sprachausgabe (`voice/tts.py`, mmx-CLI), Video über OpenRouter, Musik, Embeddings.

## Tests (rot zuerst)

- Katalog: Parser mit der echten Live-Antwort → M2.1/M2/Text-01 fehlen, M3.x vorhanden; Fallback ohne Netz; Nutzerliste.
- Denk-Stufen je Modell: kwargs für M3.1-Flash (adaptive + effort, ohne temperature, nie disabled), M3 (mit/ohne Stufe), M2.7 (Legacy).
- Bilder: M3.x unverändert, M2.x umgebaut.
- Preise: Kostenberechnung M3.1-Flash/M3 inkl. Cache-Lesen.
- Mutanten; volle Reihe (pytest `-n 16`, vitest, `tsc -b`, eslint, ruff); hydratest mit echtem Key: Katalog zeigt genau die
  antwortenden Modelle, Chat mit M3.1-Flash und M3 inkl. Werkzeugaufruf und Bild, Kosten erscheinen.
