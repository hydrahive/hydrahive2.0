# Ollama über /api/chat ansprechen (Werkzeuge für lokale Agenten)

Task 3474c703. Stand 29.10.2026.

## Problem

Ein lokaler Agent mit Ollama (Test-Spezialist, `gemma4:12b` bzw. `gpt-oss:20b`, RTX 5060 Ti) löste eine leichte
Aufgabe richtig. Bei einer etwas längeren brach er ab:

- `gemma4:12b` rief dreimal ein Werkzeug „none“ ohne Argumente auf → Schleifenschutz.
- `gpt-oss:20b` lieferte gleich in Runde 1 eine leere Antwort.

## Ursache

HydraHive ruft Ollama über LiteLLM mit dem Präfix `ollama/` auf. In LiteLLM 1.105.1 ist das die alte Anbindung an
**`/api/generate`**. Sie kennt kein echtes Werkzeug-Feld: Die Werkzeuge werden in den Prompt geschrieben, und die
Antwort wird als JSON geraten. Nachgestellt mit dem echten Verlauf des abgebrochenen Laufs (je 3 Versuche):

| Route | gemma4:12b | gpt-oss:20b |
|---|---|---|
| `ollama/` (`/api/generate`, heute) | 3× erfundenes Werkzeug | 3× erfundenes Werkzeug |
| `ollama_chat/` (`/api/chat`) | 3× fertige Textantwort | 3× fertige Textantwort |

Die Antwort von `gpt-oss:20b` über `/api/chat` war inhaltlich richtig (Datei, drei Werte, sechs Fundstellen).
Ollama selbst liefert die Werkzeugaufrufe über `/api/chat` korrekt, mit und ohne Streaming.

Die zweite Route ist auch die, die Ollama für Chat und Werkzeuge vorsieht. LiteLLM reicht dort `num_ctx` und `think`
durch.

## Änderung

1. Ein Baustein in `llm/_routing.py`: `litellm_model(model)` macht aus `ollama/<name>` das LiteLLM-Ziel
   `ollama_chat/<name>`. Alle anderen Modelle bleiben unverändert.
2. Ihn benutzen alle Chat-Aufrufe an LiteLLM:
   - `runner/_llm_bridge_backends.litellm_call` (Agenten, Benchmark, Fähigkeits-Prüfung)
   - `llm/client.complete` und `llm/client.stream`
3. **Unverändert:**
   - Die Modell-ID heißt weiter `ollama/<name>`: in `llm.json`, an Agenten, im Katalog, in `llm_calls` und in der
     Kontext-Berechnung (`context_window_for`, `num_ctx_for_ollama`). Nichts muss umgetragen werden.
   - `num_ctx` und `api_base` gehen wie bisher mit.
   - Embeddings (`llm/embed.py`) haben einen eigenen Weg (`/api/embed`) und werden nicht angefasst.

## Nicht Teil dieser Änderung

- Ob ein Modell eine schwere Aufgabe schafft, ist eine Frage des Modells. Gemessen wird das danach mit einem echten
  Agenten-Lauf.
- Ein eigener Streaming-Weg für Ollama-Agenten (heute gibt es den Fallback ohne Streaming).

## Prüfung

- Vertragstests: Ollama-Ziel ist `ollama_chat/…` in `litellm_call`, `complete` und `stream`. Andere Anbieter
  unverändert. `num_ctx`/`api_base` weiterhin gesetzt. Die Modell-ID in `llm_calls` bleibt `ollama/…`.
- Rot gegen `main`, grün danach, Mutanten.
- Echter Agenten-Lauf mit dem Test-Spezialisten (die schwerere Aufgabe aus dem Task) mit `gemma4:12b` und
  `gpt-oss:20b` auf hydratest.
