from __future__ import annotations

# `ask_agent` ist optional und wird zur Laufzeit gefiltert (siehe unten) —
# nur wenn AgentLink konfiguriert ist (settings.agentlink_url), sonst würde
# der Master ein Tool sehen das nur Stub-Fehler zurückgibt.
_BASE_TOOLS: dict[str, list[str]] = {
    "master": [
        "shell_exec", "file_read", "file_write", "file_patch",
        "web_search", "fetch_url",
        "read_memory", "write_memory", "search_memory",
        "todo_write", "ask_agent", "send_mail", "list_projects",
        "list_skills", "load_skill",
        "webmin_status", "webmin_call",
    ],
    "project": [
        "shell_exec", "file_read", "file_write", "file_patch",
        "fetch_url",
        "read_memory", "write_memory", "search_memory",
        "todo_write", "ask_agent", "list_projects",
        "list_skills", "load_skill",
    ],
    "specialist": [
        "fetch_url", "list_skills", "load_skill",
    ],
}


def _filtered() -> dict[str, list[str]]:
    """Filtert nicht-registrierte Tools raus — primär ask_agent wenn
    AgentLink nicht konfiguriert ist."""
    from hydrahive.tools import REGISTRY  # lazy um Zyklen zu vermeiden
    return {
        agent_type: [t for t in tools if t in REGISTRY]
        for agent_type, tools in _BASE_TOOLS.items()
    }


class _LazyDefaultTools(dict):
    """dict-Wrapper der bei jedem Zugriff frisch filtert — Settings-Wechsel
    zur Laufzeit (z.B. in Tests) werden so erfasst."""
    def __getitem__(self, key):
        return _filtered()[key]
    def keys(self):
        return _BASE_TOOLS.keys()
    def items(self):
        return _filtered().items()
    def values(self):
        return _filtered().values()
    def __iter__(self):
        return iter(_BASE_TOOLS.keys())
    def __contains__(self, key):
        return key in _BASE_TOOLS
    def __len__(self):
        return len(_BASE_TOOLS)


DEFAULT_TOOLS = _LazyDefaultTools()

DEFAULT_TEMPERATURE = 0.7
# Hoch genug, damit ein Review-Agent ein 16kB-Markdown via file_write schreiben
# kann — allein das Input-JSON des Tool-Use frisst ~4-5k Tokens, plus Thinking-
# Budget, plus Text-Output drumrum. 8192 war zu knapp (siehe Issue #142,
# test_10 verlor 20% der Session-Kosten an stop_reason=max_tokens-Restarts).
DEFAULT_MAX_TOKENS = 16384
DEFAULT_THINKING_BUDGET = 0

# --- Compaction-Defaults (per-Agent overridebar) ----------------------------
# compact_model: "" = nutze llm_model des Agents, sonst Override (z.B. claude-haiku
#   für günstigere Compaction)
DEFAULT_COMPACT_MODEL = ""
# Tool-Results in der serialisierten History werden auf dieses Limit gekürzt.
# 2000 ist OpenClaw-Original. Bei riesen Sessions (Anthropic 400 "input too long")
# kann der User auf 500 runtergehen.
DEFAULT_COMPACT_TOOL_RESULT_LIMIT = 2000
# Live-Truncation: Tool-Results werden vor dem LLM-Call auf dieses Zeichenlimit
# gekürzt. Verhindert dass ein einzelner Tool-Call (z.B. 52k-JSON-Antwort eines
# fetch_url) den gesamten Context frisst. 0 = kein Limit.
DEFAULT_TOOL_RESULT_MAX_CHARS = 12_000
# Prompt-Cache-TTL für den stabilen System-Prompt-Block.
# "1h" = 1 Stunde (2x Write-Kosten, aber Cache-Hits über Sessions hinweg).
# "5m" = 5 Minuten (Anthropic-Default, günstigere Write-Kosten).
# Quelle: claude-code-source-code/src/bootstrap/state.ts:251
#   "cache TTL is ~5min"
# Claude Code-Default ist 5min (Anthropic-Default ohne extended-cache-ttl-Beta).
# Längere TTL = teurer beim Initial Write — vorher "1h" hat die Kosten verdoppelt
# ohne wirksamen Nutzen (server-side Eviction passierte trotzdem <5min).
DEFAULT_CACHE_TTL = "5m"
# Reserve-Tokens für die Summary-Antwort. Wenn used > (window - reserve) wird
# auto-compactet.
DEFAULT_COMPACT_RESERVE_TOKENS = 16_384
# Wann triggert auto-compact als % vom (Context-Window − Reserve). 75 = bei 75% Fülle.
# Senken auf 75% (von 100%) reduziert Token-Verbrauch durch häufigere Compaction.
# Mit 200k Window: compactet bei 150k statt bei 184k, spart ~20-30% per Turn vor Compact.
DEFAULT_COMPACT_THRESHOLD_PCT = 75

# --- Runner-Defaults (per-Agent overridebar) ---------------------------------
# Maximale Tool-Loop-Iterationen pro Session-Run. Wenn überschritten endet
# der Run mit Error "Max-Iterationen erreicht". Aus Token-Audit (#129/#125):
# 30 ist zu hoch — bei komplexen Aufgaben triggert das nicht das Aufgeben
# sondern einen Restart durch User (49-Call-Repo-Review-Pattern). 16 zwingt
# den Agent zu fokussierterem Vorgehen, spart durchschnittlich 30-50% Tokens.
# Komplexe Reviews können den Wert per-Agent über `max_iterations` erhöhen.
DEFAULT_MAX_ITERATIONS = 16

