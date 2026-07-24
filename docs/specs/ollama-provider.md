# Spec: Ollama als LLM-Provider

## Was
Offizielle Unterstützung von Ollama als LLM-Provider in HydraHive2. User können
einen Provider vom Typ `ollama` in der `llm.json` anlegen (mit user-eigener
`api_base`, z.B. `http://localhost:11434`) und ihre lokal installierten Modelle
für Agenten nutzen — ohne den Source zu forken.

## Warum
- Bisher gibt es keine Ollama-Anbindung. Ein Kunde hat es selbst gepatcht, ist
  aber gescheitert: Unser `apply_keys()` reicht die `api_base` nicht an LiteLLM
  durch, und `litellm_call()` übergibt kein `api_base` an `litellm.acompletion()`.
  → LiteLLM weiß nicht, wohin die Anfrage soll.
- Lokale Modelle (Datenschutz, Kosten, Offline) sind ein wiederkehrender Wunsch.

## Wie (grob)
Ollama spricht eine OpenAI-kompatible API. Damit läuft es über den bestehenden
LiteLLM-Pfad — es fehlen nur zwei Dinge: die **Base-URL durchreichen** und das
**Live-Model-Listing** gegen die user-eigene URL.

1. **`_config.py`** — neuer Helper `provider_api_base(config, provider_id)`, der
   die `api_base` eines Providers aus der `llm.json` liest. `ollama` wird in
   `_ENV_MAP` aufgenommen (`OLLAMA_API_KEY`), da Ollama optional einen Key kennt
   (Ollama-Cloud/geschützte Instanzen) — lokal wird kein Key gesetzt.

2. **`_llm_bridge_backends.py` / `llm_bridge.py`** — `litellm_call()` bekommt
   optional `api_base` und reicht es an `litellm.acompletion(api_base=...)` durch.
   `call_with_tools()` liest die `api_base` des Ziel-Providers aus der Config und
   gibt sie weiter. Nicht-Ollama-Provider bleiben unberührt (api_base=None → kein
   kwarg gesetzt).

3. **`catalog.py`** — Ollama-Live-Listing: die URL kommt aus der user-`api_base`
   (`{api_base}/v1/models`), nicht aus hardcodierten `PROVIDER_ENDPOINTS`. Ollama
   braucht lokal keinen API-Key → der `configured`/`key`-Gate wird für Ollama
   gelockert (Provider mit gesetzter `api_base` gilt als konfiguriert).

4. **`_catalog_data.py`** — `PROVIDER_PREFIX["ollama"] = "ollama/"` (LiteLLM-Route).
   Keine STATIC_MODELS-Hardcodes — Modelle kommen live vom user-Endpoint. Modelle
   ohne METADATA-Eintrag werden als `unknown: True` markiert (bestehendes Verhalten),
   `tool_use: None` (unbekannt) — kein falsches Versprechen.

## Tool-Calls
Ollama-Modelle mit nativem Function-Calling (llama3.1+, mistral-nemo, qwen2.5,
firefunction etc.) funktionieren direkt über den bestehenden `tool_calls`-Pfad.
Modelle **ohne** natives Function-Calling geben Tool-Calls u.U. als Text-JSON aus
— das wird **nicht** geparst (bewusste Entscheidung: ein Text-Fallback-Parser wäre
ein Security-Risiko, weil legitimes JSON fälschlich als Tool-Call ausgeführt werden
könnte). Solche Modelle sind chat-only. Wird dokumentiert.

## Sicherheit
- `api_base` ist **frei wählbar** (bewusste Entscheidung, Option a): erlaubt auch
  Remote-Ollama auf anderem Host. Damit besteht eine SSRF-Fläche — ein Admin, der
  einen Provider anlegt, kann HydraHive HTTP-Requests an beliebige (auch interne)
  URLs schicken lassen. Das liegt in der Verantwortung des Provider-Admins, der
  ohnehin privilegierten Zugriff hat. Kein automatisches Whitelisting.
- `OLLAMA_API_KEY` wird über `provider_env_vars()` automatisch in die
  shell_exec-Denylist aufgenommen (bestehender Mechanismus via `_ENV_MAP`).

## Akzeptanzkriterien
- [ ] Ein `ollama`-Provider mit `api_base` in `llm.json` reicht die Base-URL an
      `litellm.acompletion()` durch (Test mit gemocktem litellm).
- [ ] `provider_api_base()` liefert die api_base des richtigen Providers, `None`
      wenn nicht gesetzt.
- [ ] Nicht-Ollama-Provider setzen **kein** `api_base`-kwarg (Regression-Schutz).
- [ ] Catalog listet Ollama-Modelle live vom user-Endpoint; ohne api_base leere
      Liste, kein Crash.
- [ ] Ollama gilt auch ohne API-Key als `configured`, wenn `api_base` gesetzt ist.
- [ ] `ruff` + bestehende Tests grün, keine zirkulären Imports.

## Nicht in diesem Plan
- Text-basierter Tool-Call-Fallback-Parser (Security-Risiko, separat + Review).
- Kosten-/Pricing-Feinheiten für Ollama (bleibt beim bestehenden „ollama"-Label).
- Frontend-UI-Änderungen (Provider wird über bestehende llm.json/Provider-Maske
  angelegt).
