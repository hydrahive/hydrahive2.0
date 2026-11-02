# Codex-OAuth: erweitertes Kontextfenster

## Was

HydraHive verwendet bei `openai-codex` das accountbezogene `max_context_window` des ChatGPT/Codex-Modellkatalogs als effektives Kontextfenster. Die automatische Kompaktierung wird spätestens bei 90 Prozent dieses Fensters ausgelöst, sofern der Katalog keine kleinere explizite Grenze liefert.

Für Tills aktuellen OAuth-Account meldet der Live-Katalog für `gpt-5.6-sol`:

- Standardfenster: 272.000 Tokens
- maximales Fenster: 872.000 Tokens
- explizite Auto-Kompaktierungsgrenze: nicht gesetzt
- daraus abgeleitete Obergrenze: 784.800 Tokens (90 Prozent)

## Warum

HydraHive nutzt den Codex-OAuth-Responses-Endpunkt direkt und liest keine lokale Codex-CLI-`config.toml`. Bisher verdeckt die statische Modellmetadaten-Tabelle den bereits live geladenen accountbezogenen Kontextwert. Dadurch kann HydraHive das vom OAuth-Backend angebotene größere Fenster nicht nutzen.

Der OpenAI-API-Key-Pfad ist ausdrücklich nicht Teil dieser Änderung. Es wird kein API-Guthaben verwendet.

## Wie

1. Der Codex-Katalogparser übernimmt `max_context_window`, wenn es eine positive Ganzzahl und mindestens so groß wie `context_window` ist.
2. Für Codex wird die Auto-Kompaktierungsobergrenze aus `auto_compact_token_limit` übernommen. Fehlt sie, gilt 90 Prozent des effektiven Fensters.
3. Die Modell-Registry speichert Kontextfenster und Auto-Kompaktierungsgrenze aus dem Live-Katalog.
4. `context_window_for()` bevorzugt ausschließlich für `openai-codex/*` die accountbezogenen Registry-Werte vor statischen Metadaten. Bei fehlendem Live-Katalog bleibt der bisherige statische Fallback erhalten.
5. Die bestehende pro Agent konfigurierte frühere Kompaktierung bleibt wirksam. Die Modellgrenze ist nur eine Obergrenze: Ein Agent mit 75 Prozent kompaktet weiterhin bei 75 Prozent; ein Agent mit 95 oder 100 Prozent spätestens bei der Codex-Grenze.
6. Es wird kein zusätzlicher Parameter an den Responses-Endpunkt gesendet; die Änderung betrifft die lokale History-/Kompaktierungssteuerung passend zum servergemeldeten Maximum.

## Akzeptanzkriterien

- Der Codex-Katalog bildet 272.000 Standard / 872.000 Maximum auf 872.000 effektiven Kontext ab.
- Ohne explizites Limit wird für 872.000 eine Auto-Kompaktierungsobergrenze von 784.800 berechnet.
- Ein explizites kleineres `auto_compact_token_limit` wird respektiert.
- Live-Metadaten überschreiben bei Codex den statischen 372k-Fallback.
- Ohne Live-Metadaten bleibt der statische Fallback erhalten.
- Eine Agentenschwelle unter 90 Prozent bleibt unverändert wirksam.
- Eine Agentenschwelle über 90 Prozent wird auf die Modellgrenze begrenzt.
- Andere Provider ändern ihr Verhalten nicht.
- Bestehende Katalog-, Registry- und Kompaktierungstests bleiben grün.

## Nicht enthalten

- OpenAI-API-Key oder Abrechnung über OpenAI-API-Guthaben
- künstliches Überschreiten des vom OAuth-Katalog gemeldeten Maximums
- Änderung der Agentenkonfigurationen auf einen höheren Prozentwert
- großer synthetischer 800k-Live-Prompt
