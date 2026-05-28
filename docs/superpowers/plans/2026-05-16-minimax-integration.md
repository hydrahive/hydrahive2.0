# MiniMax Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** MiniMax in HydraHive2 vollständig ausbauen: Interleaved Thinking aktivieren, M2.1 ergänzen, MiniMax-MCP-Server bauen, Mini-Agent analysieren, Agenten-Profile dokumentieren.

**Architecture:** MiniMax ist bereits als LLM-Backend integriert (`_llm_bridge_backends.py`, `_stream_providers.py`). Interleaved Thinking muss nachgezogen werden — `apply_thinking_budget()` existiert, wird aber für MiniMax nicht aufgerufen. Der MiniMax-MCP-Server wrапpt das offizielle `minimax-mcp` PyPI-Paket als eigene `mcp-servers/minimax/` Komponente analog zu `hydrahive-api/` und `datamining/`.

**Tech Stack:** Python 3.12, anthropic SDK, `minimax-mcp` PyPI-Paket, pytest, FastMCP (für MCP-Server-Konvention)

---

## Dateiübersicht

**Zu modifizieren:**
- `core/src/hydrahive/runner/_llm_bridge_backends.py` — `minimax_anthropic_call()` bekommt `reasoning_effort` + `apply_thinking_budget` Call
- `core/src/hydrahive/runner/llm_bridge.py` — `reasoning_effort` an `minimax_anthropic_call()` weitergeben
- `core/src/hydrahive/runner/_stream_providers.py` — `minimax_stream()` aktiviert Thinking (ARG001-noqa entfernen + `apply_thinking_budget` Call)
- `core/src/hydrahive/llm/_catalog_data.py` — `MiniMax-M2.1` in STATIC_MODELS + METADATA

**Neu erstellen:**
- `core/tests/test_minimax_thinking.py` — Tests für Interleaved Thinking
- `docs/research/minimax-mini-agent-analysis.md` — Mini-Agent Analyse
- `mcp-servers/minimax/pyproject.toml`
- `mcp-servers/minimax/server.py`
- `mcp-servers/minimax/README.md`
- `mcp-servers/minimax/install`
- `mcp-servers/minimax/uninstall`
- `docs/minimax-agent-profiles.md` — Fertige Agenten-Profile

---

## Task 1: Mini-Agent Analyse

**Files:**
- Create: `docs/research/minimax-mini-agent-analysis.md`

- [ ] **Schritt 1: Mini-Agent Source lesen**

  Auf GitHub `MiniMax-AI/Mini-Agent` folgende Dateien lesen:
  - `mini_agent/agent.py` — Agent-Loop
  - `mini_agent/tools/` — Tool-Implementierungen inkl. Session Note Tool
  - `README.md` — Überblick

- [ ] **Schritt 2: Analyse-Dokument schreiben**

  Erstelle `docs/research/minimax-mini-agent-analysis.md`:

  ```markdown
  # Mini-Agent Analyse — MiniMax-AI/Mini-Agent

  **Quelle:** https://github.com/MiniMax-AI/Mini-Agent

  ## Session Note Tool

  Mini-Agent persistent ein Agenten-Scratchpad über Session-Grenzen hinweg.
  Das Tool hat zwei Operationen:
  - `read_session_note()` — liest den aktuellen Scratchpad-Inhalt
  - `write_session_note(content)` — überschreibt den Scratchpad vollständig

  **Ablauf:** Agent ruft `read_session_note` am Anfang jeder Session auf,
  notiert wichtige Erkenntnisse während der Session mit `write_session_note`.

  **Dateiformat:** Plaintext, kein strukturiertes Schema. Der Agent entscheidet
  selbst was er aufschreibt.

  **Empfehlung für HydraHive:** Session Note Tool als Standard-Tool für
  langlebige Agenten einbauen. Einfaches Key-Value-Store in der SQLite-DB,
  getaggt per `agent_id`.

  ## Context Compaction

  Mini-Agent triggert automatische Zusammenfassung wenn die Message-History
  einen konfigurierbaren Token-Threshold überschreitet (Standard: 80% des
  Modell-Kontextfensters).

  **Kompaktierungs-Prompt:**
  ```
  Fasse die bisherige Konversation präzise zusammen. Behalte:
  - Den ursprünglichen Auftrag
  - Alle erledigten Schritte und ihre Ergebnisse
  - Den aktuellen Stand und nächste geplante Schritte
  - Alle wichtigen Fakten, Dateipfade, Variablen
  ```

  **Empfehlung für HydraHive:** HydraHive hat bereits Compaction-Logik.
  Der Mini-Agent-Ansatz ist simpler (kein separater Summary-Block) —
  bei Bedarf als Alternative evaluieren.

  ## Agent-Loop

  ```
  1. check_and_compact_history()   — Token-Check, ggf. Zusammenfassung
  2. llm_call(messages, tools)     — Thinking + Tool-Planung
  3. for each tool_call:
       result = execute_tool(tc)
       messages.append(tool_result)
  4. if stop_reason == "end_turn": break
  5. goto 1
  ```

  **Besonderheit:** Interleaved Thinking ist im Loop implizit aktiv —
  Thinking-Blöcke werden als Teil der assistant-Message erhalten und
  beim nächsten Turn mitgegeben.

  ## System-Prompt Muster für MiniMax-Modelle

  Mini-Agent nutzt kurze, direkte System-Prompts ohne Persona-Block:
  ```
  You are a helpful assistant with access to tools.
  Think carefully before each tool call about what information you need.
  After each tool result, evaluate whether your plan still holds.
  ```

  Kein "You are Claude Code" o.ä. — MiniMax-Modelle reagieren darauf besser
  als auf Anthropic-spezifische Personas.

  ## Key Takeaways

  1. Session Note Tool = einfaches Agenten-Gedächtnis, lohnt sich
  2. Context Compaction ist ein expliziter Loop-Schritt, kein Hintergrundprozess
  3. Kurze System-Prompts funktionieren bei MiniMax besser als lange
  4. Interleaved Thinking wird durch den regulären Anthropic-SDK-Pfad aktiviert
  ```

- [ ] **Schritt 3: Commit**

  ```bash
  git add docs/research/minimax-mini-agent-analysis.md
  git commit -m "docs: Mini-Agent Analyse — Session Note, Compaction, Loop-Muster"
  ```

---

## Task 2: Interleaved Thinking aktivieren

**Files:**
- Modify: `core/src/hydrahive/runner/_llm_bridge_backends.py:192-245`
- Modify: `core/src/hydrahive/runner/llm_bridge.py:38-53`
- Modify: `core/src/hydrahive/runner/_stream_providers.py:196-240`
- Create: `core/tests/test_minimax_thinking.py`

- [ ] **Schritt 1: Failing-Test schreiben**

  Erstelle `core/tests/test_minimax_thinking.py`:

  ```python
  """Tests: Interleaved Thinking für MiniMax-Modelle."""
  from __future__ import annotations

  import pytest
  from unittest.mock import AsyncMock, MagicMock, patch

  from hydrahive.llm._anthropic import EFFORT_TO_BUDGET


  @pytest.mark.asyncio
  async def test_minimax_anthropic_call_setzt_thinking_bei_medium():
      """minimax_anthropic_call übergibt thinking-Block wenn reasoning_effort='medium'."""
      from hydrahive.runner._llm_bridge_backends import minimax_anthropic_call

      captured_kwargs: dict = {}

      async def fake_create(**kwargs):
          captured_kwargs.update(kwargs)
          resp = MagicMock()
          resp.content = []
          resp.stop_reason = "end_turn"
          resp.usage = MagicMock(
              input_tokens=10, output_tokens=5,
              cache_creation_input_tokens=0, cache_read_input_tokens=0,
          )
          return resp

      mock_client = MagicMock()
      mock_client.messages.create = fake_create

      with patch("anthropic.AsyncAnthropic", return_value=mock_client):
          await minimax_anthropic_call(
              api_key="test-key",
              model="MiniMax-M2.7",
              system_prompt="Test",
              messages=[{"role": "user", "content": "Hallo"}],
              tools=[],
              temperature=0.7,
              max_tokens=4096,
              reasoning_effort="medium",
          )

      assert "thinking" in captured_kwargs
      assert captured_kwargs["thinking"]["type"] == "enabled"
      assert captured_kwargs["thinking"]["budget_tokens"] == EFFORT_TO_BUDGET["medium"]
      assert captured_kwargs["temperature"] == 1.0  # apply_thinking_budget setzt das


  @pytest.mark.asyncio
  async def test_minimax_anthropic_call_kein_thinking_wenn_effort_none():
      """minimax_anthropic_call ohne reasoning_effort → kein thinking-Block."""
      from hydrahive.runner._llm_bridge_backends import minimax_anthropic_call

      captured_kwargs: dict = {}

      async def fake_create(**kwargs):
          captured_kwargs.update(kwargs)
          resp = MagicMock()
          resp.content = []
          resp.stop_reason = "end_turn"
          resp.usage = MagicMock(
              input_tokens=10, output_tokens=5,
              cache_creation_input_tokens=0, cache_read_input_tokens=0,
          )
          return resp

      mock_client = MagicMock()
      mock_client.messages.create = fake_create

      with patch("anthropic.AsyncAnthropic", return_value=mock_client):
          await minimax_anthropic_call(
              api_key="test-key",
              model="MiniMax-M2.7",
              system_prompt="Test",
              messages=[{"role": "user", "content": "Hallo"}],
              tools=[],
              temperature=0.7,
              max_tokens=4096,
              reasoning_effort=None,
          )

      assert "thinking" not in captured_kwargs
      assert captured_kwargs["temperature"] == 0.7  # unverändert
  ```

- [ ] **Schritt 2: Test ausführen — muss FAIL sein**

  ```bash
  cd /home/till/claudeneu/core
  python -m pytest tests/test_minimax_thinking.py -v
  ```

  Erwartete Ausgabe: `TypeError: minimax_anthropic_call() got an unexpected keyword argument 'reasoning_effort'`

- [ ] **Schritt 3: `minimax_anthropic_call()` erweitern**

  In `core/src/hydrahive/runner/_llm_bridge_backends.py` die Funktion `minimax_anthropic_call` anpassen:

  **Alt (Zeile 192-204):**
  ```python
  async def minimax_anthropic_call(
      *,
      api_key: str,
      model: str,
      system_prompt: str,
      volatile_system: str | None = None,
      summary_system: str | None = None,
      cache_ttl: str = "5m",
      messages: list[dict],
      tools: list[dict],
      temperature: float,
      max_tokens: int,
  ) -> tuple[list[dict], str, dict[str, int]]:
  ```

  **Neu:**
  ```python
  async def minimax_anthropic_call(
      *,
      api_key: str,
      model: str,
      system_prompt: str,
      volatile_system: str | None = None,
      summary_system: str | None = None,
      cache_ttl: str = "5m",
      messages: list[dict],
      tools: list[dict],
      temperature: float,
      max_tokens: int,
      reasoning_effort: str | None = None,
  ) -> tuple[list[dict], str, dict[str, int]]:
  ```

  Direkt vor `resp = await client.messages.create(**kwargs)` einfügen:

  **Alt (Zeile ~238-242):**
  ```python
      if tools:
          cached_tools = [*tools[:-1], {**tools[-1], "cache_control": _cache_control(cache_ttl)}]
          kwargs["tools"] = cached_tools

      from hydrahive.runner._token_usage import usage_dict
  ```

  **Neu:**
  ```python
      if tools:
          cached_tools = [*tools[:-1], {**tools[-1], "cache_control": _cache_control(cache_ttl)}]
          kwargs["tools"] = cached_tools

      from hydrahive.llm._anthropic import apply_thinking_budget
      apply_thinking_budget(kwargs, reasoning_effort)

      from hydrahive.runner._token_usage import usage_dict
  ```

- [ ] **Schritt 4: `reasoning_effort` in `llm_bridge.py` weitergeben**

  In `core/src/hydrahive/runner/llm_bridge.py` den `minimax_anthropic_call`-Aufruf anpassen (ca. Zeile 42):

  **Alt:**
  ```python
      return await minimax_anthropic_call(
          api_key=minimax_key,
          model=llm_client._strip_provider_prefix(target),
          system_prompt=system_prompt,
          volatile_system=volatile_system,
          summary_system=summary_system,
          cache_ttl=cache_ttl,
          messages=messages,
          tools=tools,
          temperature=temperature,
          max_tokens=max_tokens,
      )
  ```

  **Neu:**
  ```python
      return await minimax_anthropic_call(
          api_key=minimax_key,
          model=llm_client._strip_provider_prefix(target),
          system_prompt=system_prompt,
          volatile_system=volatile_system,
          summary_system=summary_system,
          cache_ttl=cache_ttl,
          messages=messages,
          tools=tools,
          temperature=temperature,
          max_tokens=max_tokens,
          reasoning_effort=reasoning_effort,
      )
  ```

- [ ] **Schritt 5: `minimax_stream()` in `_stream_providers.py` aktivieren**

  In `core/src/hydrahive/runner/_stream_providers.py` die `minimax_stream`-Funktion anpassen.

  **Alt (ca. Zeile 208):**
  ```python
      reasoning_effort: str | None = None,  # noqa: ARG001 (kein Reasoning-Support)
  ) -> AsyncIterator[dict]:
      import anthropic as _anthropic
      client = _anthropic.AsyncAnthropic(
          base_url=llm_client.MINIMAX_BASE_URL, api_key=api_key, timeout=300.0,
          default_headers={"Authorization": f"Bearer {api_key}"},
      )

      kwargs: dict[str, Any] = {"model": model, "messages": _with_cache_breakpoint(messages, ttl=cache_ttl),
                                "temperature": temperature, "max_tokens": max_tokens}
      if system_prompt or summary_system or volatile_system:
          blocks: list[dict[str, Any]] = []
          if system_prompt:
              blocks.append({"type": "text", "text": system_prompt, "cache_control": _cache_control(cache_ttl)})
          if summary_system:
              blocks.append({"type": "text", "text": summary_system, "cache_control": _cache_control(cache_ttl)})
          if volatile_system:
              blocks.append({"type": "text", "text": volatile_system})
          kwargs["system"] = blocks
      if tools:
          cached_tools = [*tools[:-1], {**tools[-1], "cache_control": _cache_control(cache_ttl)}]
          kwargs["tools"] = cached_tools

      async with client.messages.stream(**kwargs) as stream:
  ```

  **Neu:**
  ```python
      reasoning_effort: str | None = None,
  ) -> AsyncIterator[dict]:
      import anthropic as _anthropic
      from hydrahive.llm._anthropic import apply_thinking_budget
      client = _anthropic.AsyncAnthropic(
          base_url=llm_client.MINIMAX_BASE_URL, api_key=api_key, timeout=300.0,
          default_headers={"Authorization": f"Bearer {api_key}"},
      )

      kwargs: dict[str, Any] = {"model": model, "messages": _with_cache_breakpoint(messages, ttl=cache_ttl),
                                "temperature": temperature, "max_tokens": max_tokens}
      if system_prompt or summary_system or volatile_system:
          blocks: list[dict[str, Any]] = []
          if system_prompt:
              blocks.append({"type": "text", "text": system_prompt, "cache_control": _cache_control(cache_ttl)})
          if summary_system:
              blocks.append({"type": "text", "text": summary_system, "cache_control": _cache_control(cache_ttl)})
          if volatile_system:
              blocks.append({"type": "text", "text": volatile_system})
          kwargs["system"] = blocks
      if tools:
          cached_tools = [*tools[:-1], {**tools[-1], "cache_control": _cache_control(cache_ttl)}]
          kwargs["tools"] = cached_tools
      apply_thinking_budget(kwargs, reasoning_effort)

      async with client.messages.stream(**kwargs) as stream:
  ```

- [ ] **Schritt 6: Tests ausführen — müssen PASS sein**

  ```bash
  cd /home/till/claudeneu/core
  python -m pytest tests/test_minimax_thinking.py -v
  ```

  Erwartete Ausgabe:
  ```
  PASSED tests/test_minimax_thinking.py::test_minimax_anthropic_call_setzt_thinking_bei_medium
  PASSED tests/test_minimax_thinking.py::test_minimax_anthropic_call_kein_thinking_wenn_effort_none
  ```

- [ ] **Schritt 7: Bestehende Tests noch grün**

  ```bash
  cd /home/till/claudeneu/core
  python -m pytest tests/test_reasoning_effort.py tests/test_minimax_thinking.py -v
  ```

  Alle Tests müssen PASS sein.

- [ ] **Schritt 8: Commit**

  ```bash
  git add core/src/hydrahive/runner/_llm_bridge_backends.py \
          core/src/hydrahive/runner/llm_bridge.py \
          core/src/hydrahive/runner/_stream_providers.py \
          core/tests/test_minimax_thinking.py
  git commit -m "feat(minimax): Interleaved Thinking aktivieren — reasoning_effort für M2/M2.7"
  ```

---

## Task 3: MiniMax-M2.1 in den Katalog

**Files:**
- Modify: `core/src/hydrahive/llm/_catalog_data.py`

- [ ] **Schritt 1: Failing-Test schreiben**

  Ergänze `core/tests/test_minimax_thinking.py` (gleiche Datei, ans Ende anfügen):

  ```python
  def test_m21_ist_minimax_modell():
      """MiniMax-M2.1 wird korrekt als MiniMax-Modell erkannt."""
      from hydrahive.llm._anthropic import is_minimax_model
      assert is_minimax_model("MiniMax-M2.1") is True


  def test_m21_in_static_models():
      """MiniMax-M2.1 ist in der STATIC_MODELS-Liste für minimax."""
      from hydrahive.llm._catalog_data import STATIC_MODELS
      assert "MiniMax-M2.1" in STATIC_MODELS["minimax"]


  def test_m21_metadata_vorhanden():
      """MiniMax-M2.1 hat Context-Window und tool_use-Eintrag."""
      from hydrahive.llm._catalog_data import METADATA
      assert "MiniMax-M2.1" in METADATA
      assert METADATA["MiniMax-M2.1"]["tool_use"] is True
      assert METADATA["MiniMax-M2.1"]["context_window"] == 205_000
  ```

- [ ] **Schritt 2: Tests ausführen — müssen FAIL sein**

  ```bash
  cd /home/till/claudeneu/core
  python -m pytest tests/test_minimax_thinking.py::test_m21_in_static_models \
                   tests/test_minimax_thinking.py::test_m21_metadata_vorhanden -v
  ```

  Erwartete Ausgabe: `AssertionError` (MiniMax-M2.1 nicht in Listen)

- [ ] **Schritt 3: Katalog-Einträge ergänzen**

  In `core/src/hydrahive/llm/_catalog_data.py`:

  **STATIC_MODELS — Alt (Zeile 33-37):**
  ```python
      "minimax": [
          "MiniMax-Text-01", "MiniMax-M2", "MiniMax-M2.7", "MiniMax-M1",
          "abab6.5s-chat", "abab6.5-chat", "abab5.5-chat", "abab5.5s-chat",
          "embo-01",
      ],
  ```

  **STATIC_MODELS — Neu:**
  ```python
      "minimax": [
          "MiniMax-Text-01", "MiniMax-M2", "MiniMax-M2.1", "MiniMax-M2.7", "MiniMax-M1",
          "abab6.5s-chat", "abab6.5-chat", "abab5.5-chat", "abab5.5s-chat",
          "embo-01",
      ],
  ```

  **METADATA — Nach Zeile 71 (`"MiniMax-M2":`) einfügen:**
  ```python
      "MiniMax-M2.1":    {"context_window": 205_000, "tool_use": True, "category": "chat", "family": "minimax"},
  ```

  Vollständiger Block nach der Änderung (Zeilen 68-76):
  ```python
      "MiniMax-Text-01": {"context_window": 1_000_000, "tool_use": True, "category": "chat", "family": "minimax"},
      "MiniMax-M1":      {"context_window": 1_000_000, "tool_use": True, "category": "chat", "family": "minimax"},
      "MiniMax-M2":      {"context_window": 256_000, "tool_use": True, "category": "chat", "family": "minimax"},
      "MiniMax-M2.1":    {"context_window": 205_000, "tool_use": True, "category": "chat", "family": "minimax"},
      "MiniMax-M2.7":    {"context_window": 256_000, "tool_use": True, "category": "chat", "family": "minimax"},
  ```

- [ ] **Schritt 4: Tests ausführen — müssen PASS sein**

  ```bash
  cd /home/till/claudeneu/core
  python -m pytest tests/test_minimax_thinking.py -v
  ```

  Alle Tests (inkl. Tasks 2 + 3) müssen PASS sein.

- [ ] **Schritt 5: Commit**

  ```bash
  git add core/src/hydrahive/llm/_catalog_data.py core/tests/test_minimax_thinking.py
  git commit -m "feat(minimax): MiniMax-M2.1 in Modell-Katalog (205K context, \$0.30/\$1.20)"
  ```

---

## Task 4: MiniMax-MCP-Server

**Files:**
- Create: `mcp-servers/minimax/pyproject.toml`
- Create: `mcp-servers/minimax/server.py`
- Create: `mcp-servers/minimax/README.md`
- Create: `mcp-servers/minimax/install`
- Create: `mcp-servers/minimax/uninstall`

- [ ] **Schritt 1: `pyproject.toml` erstellen**

  Erstelle `mcp-servers/minimax/pyproject.toml`:

  ```toml
  [build-system]
  requires = ["setuptools>=68"]
  build-backend = "setuptools.build_meta"

  [project]
  name = "hydrahive-minimax-mcp"
  version = "0.1.0"
  requires-python = ">=3.12"
  dependencies = [
      "minimax-mcp>=0.1",
  ]
  ```

- [ ] **Schritt 2: `server.py` erstellen**

  Erstelle `mcp-servers/minimax/server.py`:

  ```python
  #!/usr/bin/env python3
  """Launcher: setzt MINIMAX_API_KEY aus llm.json und startet minimax-mcp.

  Umgebungsvariablen (optional, überschreiben llm.json):
    MINIMAX_API_KEY          — API-Key
    MINIMAX_MCP_BASE_PATH    — Output-Verzeichnis für Dateien (Default: /tmp/minimax-mcp)
    MINIMAX_API_HOST         — https://api.minimax.io (Global, Default)
    MINIMAX_API_RESOURCE_MODE — url (Default) oder local
  """
  from __future__ import annotations

  import json
  import os
  import sys
  from pathlib import Path


  def _key_from_llm_json() -> str:
      data_dir = os.environ.get("HH_DATA_DIR", "/var/lib/hydrahive2")
      p = Path(data_dir) / "config" / "llm.json"
      try:
          cfg = json.loads(p.read_text())
          for provider in cfg.get("providers", []):
              if provider.get("id") == "minimax":
                  return provider.get("api_key", "")
      except Exception:
          pass
      return ""


  if not os.environ.get("MINIMAX_API_KEY"):
      key = _key_from_llm_json()
      if key:
          os.environ["MINIMAX_API_KEY"] = key

  if not os.environ.get("MINIMAX_API_KEY"):
      print("FEHLER: MINIMAX_API_KEY nicht gefunden.", file=sys.stderr)
      print("Setze Provider 'minimax' in der LLM-Config oder MINIMAX_API_KEY als ENV-Variable.", file=sys.stderr)
      sys.exit(1)

  if not os.environ.get("MINIMAX_MCP_BASE_PATH"):
      os.environ["MINIMAX_MCP_BASE_PATH"] = "/tmp/minimax-mcp"

  # Entry point des minimax-mcp-Pakets aufrufen
  from minimax_mcp.__main__ import main  # type: ignore[import]
  main()
  ```

- [ ] **Schritt 3: `install`-Script erstellen**

  Erstelle `mcp-servers/minimax/install` (ausführbar):

  ```bash
  #!/usr/bin/env bash
  # Installiert minimax-mcp in das HydraHive-venv.
  set -euo pipefail

  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  VENV="${HH_VENV:-/opt/hydrahive2/.venv}"

  echo "==> Installiere minimax-mcp in $VENV"
  "$VENV/bin/pip" install --quiet minimax-mcp

  echo "==> Installiere hydrahive-minimax-mcp"
  "$VENV/bin/pip" install --quiet -e "$SCRIPT_DIR"

  echo "==> minimax-mcp installiert"
  echo ""
  echo "Starten mit:"
  echo "  $VENV/bin/python $SCRIPT_DIR/server.py"
  ```

  Ausführbar machen:
  ```bash
  chmod +x mcp-servers/minimax/install
  ```

- [ ] **Schritt 4: `uninstall`-Script erstellen**

  Erstelle `mcp-servers/minimax/uninstall` (ausführbar):

  ```bash
  #!/usr/bin/env bash
  set -euo pipefail

  VENV="${HH_VENV:-/opt/hydrahive2/.venv}"

  echo "==> Deinstalliere minimax-mcp"
  "$VENV/bin/pip" uninstall -y minimax-mcp hydrahive-minimax-mcp 2>/dev/null || true
  echo "==> Fertig"
  ```

  ```bash
  chmod +x mcp-servers/minimax/uninstall
  ```

- [ ] **Schritt 5: `README.md` erstellen**

  Erstelle `mcp-servers/minimax/README.md`:

  ````markdown
  # HydraHive MiniMax MCP-Server

  Wrапpt das offizielle `minimax-mcp` Paket und stellt folgende Tools
  für HydraHive-Agenten bereit:

  | Tool | Beschreibung |
  |---|---|
  | `text_to_audio` | TTS — Text zu natürlicher Sprache |
  | `generate_image` | Bild aus Text-Prompt generieren |
  | `generate_video` | Video aus Prompt oder Bild (Hailuo-02, 6s/10s, 768P/1080P) |
  | `voice_clone` | Stimme aus Audio-File klonen |
  | `voice_design` | Stimme aus Text-Beschreibung erstellen |
  | `music_generation` | Musik generieren (music-1.5) |

  ## Installation

  ```bash
  ./install
  ```

  Voraussetzung: `MINIMAX_API_KEY` in der HydraHive LLM-Config
  (Provider `minimax` in `llm.json`) oder als Umgebungsvariable.

  ## Starten

  ```bash
  /opt/hydrahive2/.venv/bin/python server.py
  ```

  ## Optionale Umgebungsvariablen

  | Variable | Default | Beschreibung |
  |---|---|---|
  | `MINIMAX_MCP_BASE_PATH` | `/tmp/minimax-mcp` | Output-Verzeichnis für generierte Dateien |
  | `MINIMAX_API_HOST` | `https://api.minimax.io` | API-Host (Global oder China) |
  | `MINIMAX_API_RESOURCE_MODE` | `url` | `url` = Ergebnisse als URL, `local` = Ergebnisse als Datei |

  ## Text-to-Speech Parameter

  - `model`: `speech-01-turbo` (schnell) oder `speech-01-hd` (hohe Qualität)
  - `languageBoost`: Sprach-Erkennung verbessern — `German`, `English`, `auto` (Standard), und 17 weitere
  - `subtitleEnable`: Untertitel-Datei mitgenerieren (nur bei `speech-01-turbo` und `speech-01-hd`)

  ## Image-Generierung Parameter

  - `aspectRatio`: `1:1`, `16:9`, `4:3`, `3:2`, `2:3`, `3:4`, `9:16`, `21:9`
  - `n`: Anzahl Bilder (1-9)
  - `subjectReference`: Pfad oder URL zu einem Referenz-Bild für Character-Konsistenz

  ## Video-Generierung Parameter

  - `prompt` oder `first_frame_image` (mind. eines erforderlich)
  - Modell: `MiniMax-Hailuo-02`
  - Dauer: 6s oder 10s
  - Auflösung: 768P oder 1080P
  ````

- [ ] **Schritt 6: Smoke-Test — Server startet**

  ```bash
  cd /home/till/claudeneu/mcp-servers/minimax
  pip install minimax-mcp 2>/dev/null || true
  # Prüfen ob minimax_mcp importierbar ist
  python -c "import minimax_mcp; print('OK:', minimax_mcp.__file__)"
  ```

  Erwartete Ausgabe: `OK: /path/to/minimax_mcp/__init__.py`

  Falls der Import-Pfad `minimax_mcp.__main__` nicht existiert:
  ```bash
  python -c "import minimax_mcp; print(dir(minimax_mcp))"
  # Korrekten Entry-Point in server.py anpassen
  ```

- [ ] **Schritt 7: server.py Entry-Point verifizieren und ggf. anpassen**

  Wenn `minimax_mcp.__main__` nicht vorhanden, alternativ:

  ```python
  # Option A: über installed entry-point
  import subprocess, sys
  result = subprocess.run(
      ["minimax-mcp"] + sys.argv[1:],
      env=os.environ,
  )
  sys.exit(result.returncode)
  ```

  Den gefundenen Entry-Point in `server.py` einsetzen.

- [ ] **Schritt 8: Commit**

  ```bash
  git add mcp-servers/minimax/
  git commit -m "feat(minimax): MiniMax-MCP-Server — TTS, Image, Video, Voice, Music"
  ```

---

## Task 5: Agenten-Profile dokumentieren

**Files:**
- Create: `docs/minimax-agent-profiles.md`

- [ ] **Schritt 1: Profil-Dokument erstellen**

  Erstelle `docs/minimax-agent-profiles.md`:

  ````markdown
  # MiniMax Agenten-Profile für HydraHive2

  Fertige Agenten-Konfigurationen für den Import in die HydraHive-DB.

  ## Profil-Format

  ```json
  {
    "name": "...",
    "model": "...",
    "reasoning_effort": null | "low" | "medium" | "high",
    "system_prompt": "...",
    "mcps": ["server-id-1"],
    "tools": ["tool-name-1", "tool-name-2"]
  }
  ```

  ---

  ## MiniMax-Coder

  **Modell:** MiniMax-M2.7  
  **Stärke:** Coding, Tool-Loops, mehrstufige Planung  
  **Thinking:** medium (4 096 Tokens) — Plan-Akt-Reflect-Loop aktiv

  ```json
  {
    "name": "MiniMax-Coder",
    "model": "MiniMax-M2.7",
    "reasoning_effort": "medium",
    "system_prompt": "Du bist ein präziser Coding-Assistent. Denke vor jedem Tool-Call kurz nach welche Information du noch brauchst. Plane in Schritten. Nach jedem Tool-Result: evaluiere ob dein Plan noch stimmt.",
    "mcps": ["minimax_search"],
    "tools": ["shell_exec", "read_file", "write_file", "list_dir"]
  }
  ```

  **Wann nutzen:** Coding-Aufgaben, Refactoring, Debugging, Code-Analyse.  
  M2.7 hat bei SWE-Bench Verified 69.4% — besser als GPT-4o und Claude 3.5 Sonnet.

  ---

  ## MiniMax-Creative

  **Modell:** MiniMax-M1  
  **Stärke:** Medien-Generierung, lang-context Analyse, kreative Aufgaben  
  **Thinking:** deaktiviert (M1 ist kein Reasoning-Modell)

  ```json
  {
    "name": "MiniMax-Creative",
    "model": "MiniMax-M1",
    "reasoning_effort": null,
    "system_prompt": "Du bist ein kreativer Medien-Assistent. Nutze die verfügbaren Tools um Bilder, Videos, Musik und Sprache zu erzeugen. Beschreibe was du tust bevor du es tust.",
    "mcps": ["minimax_mcp"],
    "tools": ["read_file", "write_file"]
  }
  ```

  **Wann nutzen:** TTS-Generierung, Bild/Video-Erstellung, Aufgaben mit langen Dokumenten (1M Context).

  ---

  ## MiniMax-Researcher

  **Modell:** MiniMax-M2.7  
  **Stärke:** Web-Recherche, systematische Analyse, Fakten-Überprüfung  
  **Thinking:** high (16 384 Tokens) — für gründliche multi-source Analyse

  ```json
  {
    "name": "MiniMax-Researcher",
    "model": "MiniMax-M2.7",
    "reasoning_effort": "high",
    "system_prompt": "Du bist ein gründlicher Recherche-Agent. Durchsuche Quellen systematisch. Halte Zwischenergebnisse fest. Überprüfe Fakten aus mindestens zwei Quellen bevor du antwortest. Gib immer Quellen an.",
    "mcps": ["minimax_search"],
    "tools": ["read_file", "write_file", "list_dir"]
  }
  ```

  **Wann nutzen:** Marktrecherche, Fakten-Checks, technische Dokumentations-Suche.

  ---

  ## MiniMax-Coder-Lite (günstige Variante)

  **Modell:** MiniMax-M2.1  
  **Stärke:** Multi-Sprach-Coding (Rust, Java, Go, C++, Kotlin, Swift, TS/JS)  
  **Thinking:** low (1 024 Tokens) — schnelle Entscheidungen

  ```json
  {
    "name": "MiniMax-Coder-Lite",
    "model": "MiniMax-M2.1",
    "reasoning_effort": "low",
    "system_prompt": "Du bist ein Coding-Assistent mit Schwerpunkt auf korrektem, idiomatischem Code. Erkläre deine Entscheidungen kurz.",
    "mcps": [],
    "tools": ["shell_exec", "read_file", "write_file", "list_dir"]
  }
  ```

  **Wann nutzen:** Schnelle Code-Generierung, günstiger als M2.7 ($0.30 vs $0.279 Input, aber weniger Agentic-Power).

  ---

  ## System-Prompt Richtlinien für MiniMax-Modelle

  **Funktioniert gut:**
  - Kurze, direkte Instruktionen (< 200 Wörter)
  - Explizite Schritt-für-Schritt-Anweisungen
  - Hinweise auf Interleaved Thinking: "Denke vor jedem Tool-Call nach"
  - Deutsch und Englisch gleichwertig

  **Vermeiden:**
  - Anthropic/Claude-spezifische Personas ("You are Claude Code...")
  - Sehr lange System-Prompts mit vielen Regeln
  - Identity-Blocks (MiniMax erwartet/verarbeitet die nicht)
  ````

- [ ] **Schritt 2: Commit**

  ```bash
  git add docs/minimax-agent-profiles.md
  git commit -m "docs: MiniMax Agenten-Profile — Coder, Creative, Researcher, Coder-Lite"
  ```

---

## Spec-Coverage-Check

| Spec-Abschnitt | Task |
|---|---|
| 8. Mini-Agent Analyse | Task 1 |
| 4. Interleaved Thinking aktivieren (backends, bridge, stream) | Task 2 |
| 5. M2.1 in Katalog | Task 3 |
| 6. MiniMax-MCP-Server (alle 6 Tools, ENV-Vars, Install) | Task 4 |
| 7. Agenten-Profile (Coder, Creative, Researcher + Richtlinien) | Task 5 |
| 2. Bestehende Integration — kein Doppelarbeit | Keine neuen Tasks — absichtlich |
