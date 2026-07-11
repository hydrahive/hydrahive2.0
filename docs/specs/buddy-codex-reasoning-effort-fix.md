# Buddy Codex Reasoning Effort Fix

## Problem

Der Buddy zeigt die Reasoning-Tiefe nur für Claude und MiniMax. Codex-GPT-Modelle erhalten daher keine Bedienung. Zusätzlich verwirft der Codex-Provider den bereits aus der Session gelesenen `reasoning_effort`; seine Requests enthalten aktuell keinen `reasoning.effort`-Block. Das Speichern von „Aus“ funktioniert nicht, weil PATCH `null` als „Feld nicht gesetzt“ interpretiert.

## Ziel

Codex-GPT-Modelle erhalten modellgerechte Tiefenwerte, die Auswahl wird zuverlässig in der Session gespeichert und bei jedem Codex-Request tatsächlich an OpenAI übergeben.

## Modellregeln

- `openai-codex/gpt-5.4`, `gpt-5.4-mini`, `gpt-5.5` und `gpt-5.3-codex-spark`: `low`, `medium`, `high`, `xhigh`.
- `openai-codex/gpt-5.6-luna`: zusätzlich `max`.
- `openai-codex/gpt-5.6-sol` und `gpt-5.6-terra`: zusätzlich `max`, `ultra`.
- Die UI verwendet `null` für Standard/kein Override und sendet zum Löschen einen Leerstring.
- Veraltete `gpt-5.2`- und `gpt-5.3-codex`-Einträge werden nicht mehr als reguläre ChatGPT-Codex-Auswahl angeboten; `gpt-5.3-codex-spark` bleibt aktuell.

## Umsetzung

1. Gemeinsame Capability-API liefert pro Modell die erlaubten Effort-Werte.
2. Reasoning-Pill rendert genau diese Werte statt eines globalen Basis-/Extended-Schalters.
3. Buddy zeigt die Pill auch für `openai-codex/*`.
4. Codex-Payload übernimmt `reasoning_effort` als `reasoning: { effort }`.
5. Alle Codex-Aufrufer reichen den Session-Wert weiter.
6. PATCH löscht einen Override über `""`, ohne andere optionale Felder zu verändern.

## Akzeptanzkriterien

- Beim Buddy ist für Codex eine Tiefenauswahl sichtbar.
- Auswahl und Entfernen bleiben nach Reload erhalten.
- Codex-Requests enthalten die ausgewählte Tiefe.
- `gpt-5.4` zeigt kein `max`; `gpt-5.6-*` zeigt `max`.
- Backend- und Frontendtests sind grün.
