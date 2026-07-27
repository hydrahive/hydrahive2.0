# Tool-Gate für Modelle ohne Function-Calling

- Status: umgesetzt
- Datum: 2026-07-27
- Task: `380f4184`

## Problem

Der Runner schickt **immer** `tool_schemas` an das Modell — unabhängig davon, ob
das Modell Function-Calling überhaupt beherrscht. Bei Modellen ohne Tool-Support
(z.B. viele lokale Ollama-Modelle) führt das zu einem sichtbaren Fehlverhalten:

1. Das Modell sieht Tool-Beschreibungen im Prompt.
2. Es kann sie mangels Function-Calling nicht als echte Tool-Calls ausgeben und
   *erfindet* stattdessen Tool-Aufrufe als **Text-JSON** in der Antwort.
3. HydraHive führt dieses Text-JSON — korrekterweise — **nicht** aus.
4. Ergebnis: rohes JSON landet stumpf im Chat, der User bekommt Müll statt Antwort.

Zusätzlich kostet das unnötig Tokens: Tool-Schemas belegen bei vielen Tools
erheblichen Platz im Kontext eines Modells, das sie gar nicht nutzen kann.

## Ziel

Wenn ein Modell laut Katalog `tool_use=False` hat, werden **keine** Tools an das
Modell geschickt. Das Modell antwortet dann sauber als reiner Chat-Partner.

## Entscheidungen

### Wo greift das Gate?

In `runner/_call.py::call_with_stream_or_fallback` — der **einzigen** Stelle, an
der Modell und Tools zusammentreffen und die von beiden Pfaden (Streaming und
non-streaming Fallback) durchlaufen wird.

Bewusst **nicht** in `runner.py`, wo `tool_schemas` gebaut wird: dort ist das
Modell noch gar nicht final. `primary_model` wird pro Iteration neu aufgelöst
(Session-Override), und die Fallback-Kette kann auf ein Modell mit anderer
Tool-Fähigkeit wechseln. Das Gate muss also **pro Modell** greifen, nicht einmal
pro Session — sonst bekäme ein Fallback-Modell die falsche Behandlung.

### Woher kommt `tool_use`?

Neue SSOT-Funktion `llm/tool_support.py::model_supports_tools(model)`.

Reihenfolge:

1. **Registry-Cache** (`llm/registry.py::_cache`) — die kanonische Modell-Liste.
   Sie aggregiert `catalog_for_providers()` und enthält damit auch die
   Ollama-Modelle mitsamt der aus `/api/show` gelesenen Tool-Capability.
2. **Statische `METADATA`** — Fallback für Cloud-Modelle (exakter Key, dann ohne
   Provider-Prefix).
3. **Default `True`** — unbekannte Modelle behalten Tools.

Der Default ist bewusst `True` (fail-open): ein Modell fälschlich ohne Tools zu
lassen würde einen funktionierenden Agenten stillschweigend entmachten. Der
umgekehrte Fehler (Tools an ein Modell, das sie nicht kann) ist das bereits
bekannte, sichtbare und harmlosere Verhalten.

**Warum die Registry und nicht der Catalog-Cache?** Ollama-Modelle stehen weder
in `METADATA` noch im Catalog-Cache: `catalog_for_providers()` behandelt Ollama
in einem Sonderzweig, der `_cached_fetch()` — und damit `catalog._cache` —
komplett umgeht. Ein Lookup gegen METADATA oder den Catalog-Cache hätte also
ausgerechnet den gemeldeten Bug-Fall (lokales Ollama-Modell ohne Tools)
verfehlt. Die Registry ist die einzige Ebene, auf der beide Welten
zusammenlaufen.

Dafür bekommt `ModelEntry` ein neues Feld `tool_use: bool | None`, das `_build()`
aus dem Katalog-Eintrag durchreicht und `_add()` beim Deduplizieren mitführt.

Der Registry-Cache wird **nur gelesen, nie gefüllt** — kein Netzwerk-Call im
heißen Pfad des Runners. Er wird beim Start via `awarm()` im Lifespan gewärmt,
ist also im Normalbetrieb warm. Ist er ausnahmsweise kalt, greift METADATA bzw.
der `True`-Default. Das Gate ist damit eine Optimierung, kein harter Blocker.

### Was passiert mit den Tool-Namen im System-Prompt?

Nichts. Der System-Prompt bleibt unverändert. Das Gate entfernt ausschließlich
die `tools`-Parameter am API-Call. Grund: der Prompt ist gecacht (Anthropic
Prompt-Caching) — ihn modellabhängig zu variieren würde den Cache brechen und
wäre teurer als der eingesparte Platz.

## Umsetzung

- `core/src/hydrahive/llm/tool_support.py` (neu, ~45 Zeilen)
  - `model_supports_tools(model: str) -> bool`
- `core/src/hydrahive/llm/registry.py`
  - `ModelEntry.tool_use: bool | None` + Durchreichen in `_build()`/`_add()`
- `core/src/hydrahive/runner/_call.py`
  - `_tools_for(model, tools)` — filtert pro Modell, loggt einmal auf INFO
  - greift im Streaming-Pfad **und** in der Fallback-Schleife
- `core/tests/test_tool_gate_non_tool_models.py` (neu)

## Verifikation

- Modell mit `tool_use=False` (METADATA) → `tools=[]` am Call
- Ollama-Modell aus der Registry ohne Tool-Capability → `tools=[]`
- Ollama-Modell mit `capabilities: ["tools"]` → Tools bleiben
- Unbekanntes Modell → Tools bleiben (fail-open)
- Fallback-Kette: tool-loses Primary → `tools=[]`, fähiges Fallback behält Tools
- Die vom Runner übergebene `tools`-Liste wird nicht in-place mutiert
