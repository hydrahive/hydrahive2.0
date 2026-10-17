# llm.client: eigene Adresse des Anbieters (api_base) auch außerhalb des Agenten-Chats nutzen

## Problem (geprüft am 17.10. auf hydratest)

In der LLM-Seite kann man bei einem Anbieter eine eigene Adresse hinterlegen (`api_base` in `llm.json`), zum Beispiel
für Ollama, LM Studio oder vLLM auf einem anderen Rechner. Der Agenten-Chat beachtet sie
(`runner/llm_bridge.py` → `_resolve_api_base` → `litellm_call(api_base=…)`).

`hydrahive.llm.client.complete()` und `stream()` rufen `litellm.acompletion` aber **ohne** `api_base` auf. Nachgestellt
mit dem Anbieter `openai` und `api_base=http://127.0.0.1:18998/v1`: Die Anfrage ging an die echte OpenAI („Incorrect API
key provided … platform.openai.com“), nicht an die eingetragene Adresse.

Betroffen sind alle, die `llm.client` nutzen:
- im Kern: Zahnfee und der „Test“-Knopf der LLM-Seite (`api/routes/llm.py`, `api/routes/llm_catalog.py`);
- in den Modulen: Studio- und Atelier-Regie, Storyteller (Ghostwriter, Gliederung, Interview, Kapitel-Zusammenfassungen,
  KI-Werkzeuge), Deepresearch, Haushaltsbuch (Kategorien) und Schach.

Wer etwa nur Ollama auf einem anderen Rechner nutzt, bei dem läuft der Chat, diese Funktionen schlagen aber fehl bzw.
gehen an einen fremden Dienst. Der „Test“-Knopf meldet dann einen Fehler, obwohl die Einstellung stimmt.

## Lösung

- `_resolve_api_base(cfg, model)` zieht von `runner/llm_bridge.py` in die neue Datei `llm/_routing.py` und heißt dort
  `api_base_for(cfg, model)`. Eine eigene Datei, weil `llm/_config.py` schon 177 Zeilen hat. Die Paketschichtung bleibt so richtig: `llm` hängt nicht von `runner` ab. Das Verhalten
  bleibt gleich: Der Präfix im Modellnamen (`ollama/`, `openai/` …) führt über `PROVIDER_PREFIX` zum Anbieter, und
  dessen `api_base` wird verwendet. Ohne eingetragene Adresse gibt es kein `api_base`-Argument; Cloud-Anbieter behalten
  ihr normales Ziel.
- `runner/llm_bridge.py` nutzt `api_base_for`. Den Namen `_resolve_api_base` gibt es dort weiter als Alias, damit
  nichts bricht, was ihn noch nutzt.
- `llm/client.py`: `complete()` und `stream()` geben `api_base` an `litellm.acompletion` weiter, aber nur wenn gesetzt.
  Für `ollama/`-Modelle geht wie im Chat zusätzlich `num_ctx` mit, damit Ollama lange Eingaben nicht auf 4096 Token
  abschneidet.
- MiniMax, Claude und ChatGPT (Codex) sind nicht betroffen. Sie haben eigene Wege und keine frei wählbare Adresse.

**Bestehende Installationen:** Ohne eingetragene Adresse ändert sich nichts (gleiche Argumente wie bisher). Mit
eingetragener Adresse gehen die Anfragen jetzt dorthin, wohin sie gehören.

## Tests (TDD)

`core/tests/test_llm_client_api_base.py`:
1. `complete()` mit `openai/x` und `api_base` am Anbieter `openai` → `acompletion` bekommt diese `api_base`.
2. `stream()` genauso.
3. Ohne `api_base` am Anbieter gibt es **kein** `api_base`-Argument (Cloud-Ziel bleibt).
4. `ollama/llama3` → `api_base` des Anbieters `ollama` und `num_ctx` (+ `extra_body.options.num_ctx`).
5. Ein Anbieter mit Adresse, aber Modell eines anderen Anbieters (`groq/x`) → kein `api_base` (keine Verwechslung).
6. `api_base_for` liegt in `llm/_routing.py`. `runner/llm_bridge._resolve_api_base` ist dieselbe Funktion (Alias).

Gegenprobe auf `main`: 1, 2, 4 und 6 müssen rot sein. Bestehende Ollama-/Runner-Tests bleiben grün.

## Prüfung

- Volle Suite (TMPDIR unter `/tmp`), ruff, Mutanten.
- hydratest: Test-Server mit `api_base` einrichten. Danach müssen der Studio-Regie-Agent („In Shots zerlegen“) und der
  „Test“-Knopf der LLM-Seite dorthin gehen (Log des Test-Servers zeigt die Anfrage). Danach wird `llm.json` per
  Prüfsumme zurückgestellt.
- Ein frischer 26.04-Container ist nicht nötig, weil Installer und Start nicht betroffen sind.
