from __future__ import annotations

import contextlib
import fcntl
import json
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hydrahive.settings import settings
from hydrahive.tools._sessions import session_increment_observations

# ---------------------------------------------------------------------------
# Typen
# ---------------------------------------------------------------------------

RawObservation = dict[str, Any]

# Hook-Typen analog zu agentmemory HookType
HOOK_POST_TOOL_USE = "post_tool_use"
HOOK_POST_TOOL_FAILURE = "post_tool_failure"
HOOK_CONVERSATION = "conversation"

# Tool-Output wird auf diese Länge gekürzt bevor es gespeichert wird.
# Der Compress-Schritt (#61) extrahiert danach strukturierte Facts.
_OUTPUT_TRUNCATE_CHARS = 4000
_INPUT_TRUNCATE_CHARS = 2000


# ---------------------------------------------------------------------------
# Storage-Helpers
# ---------------------------------------------------------------------------

def _obs_file(agent_id: str, session_id: str) -> Path:
    """JSONL-Datei pro Session — append-only, kein Re-Write bei jedem Tool-Call."""
    return settings.agents_dir / agent_id / "observations" / f"{session_id}.jsonl"


@contextlib.contextmanager
def _exclusive_lock(path: Path):
    """Exclusive flock auf eine Lock-Datei neben `path`."""
    lock_path = path.with_suffix(".lock")
    with lock_path.open("a") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_obs_id() -> str:
    """Einfache ID: obs_{timestamp_ms}_{random}"""
    ts = int(time.time() * 1000)
    rand = secrets.token_hex(4)
    return f"obs_{ts}_{rand}"


def _truncate(value: Any, max_chars: int) -> Any:
    """
    Kürzt Strings und serialisierte Dicts auf max_chars.
    Andere Typen werden zu String konvertiert und dann gekürzt.
    Gibt immer einen JSON-serialisierbaren Wert zurück.
    """
    if value is None:
        return None
    if isinstance(value, str):
        if len(value) <= max_chars:
            return value
        return value[:max_chars] + f"…[{len(value) - max_chars} Zeichen gekürzt]"
    try:
        serialized = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        serialized = str(value)
    if len(serialized) <= max_chars:
        return value  # Original zurückgeben wenn klein genug
    return serialized[:max_chars] + f"…[{len(serialized) - max_chars} Zeichen gekürzt]"


# ---------------------------------------------------------------------------
# Öffentliche API
# ---------------------------------------------------------------------------

def record_observation(
    agent_id: str,
    session_id: str,
    tool_name: str,
    tool_input: Any,
    tool_output: Any,
    hook_type: str = HOOK_POST_TOOL_USE,
) -> RawObservation:
    """
    Speichert eine RawObservation nach einem Tool-Call.
    Append-only in JSONL — nie die ganze Datei neu schreiben.
    Tool-Input und -Output werden vor dem Speichern gekürzt.
    Erhöht den observation_count der Session (fire-and-forget).
    """
    obs: RawObservation = {
        "id": _generate_obs_id(),
        "session_id": session_id,
        "agent_id": agent_id,
        "timestamp": _now_iso(),
        "hook_type": hook_type,
        "tool_name": tool_name,
        "tool_input": _truncate(tool_input, _INPUT_TRUNCATE_CHARS),
        "tool_output": _truncate(tool_output, _OUTPUT_TRUNCATE_CHARS),
        "compressed": False,
        "compressed_id": None,
    }

    path = _obs_file(agent_id, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _exclusive_lock(path):
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obs, ensure_ascii=False) + "\n")

    session_increment_observations(agent_id, session_id)
    return obs


def list_raw_observations(
    agent_id: str,
    session_id: str,
    *,
    uncompressed_only: bool = False,
) -> list[RawObservation]:
    """
    Lädt alle RawObservations einer Session aus der JSONL-Datei.
    uncompressed_only=True gibt nur noch nicht komprimierte zurück (für #61).

    Known Limitation: Lädt die komplette JSONL in RAM.
    Bei sehr langen Sessions (1000+ Observations) könnte das eng werden.
    Für den aktuellen Scope irrelevant.
    """
    path = _obs_file(agent_id, session_id)
    if not path.exists():
        return []

    observations: list[RawObservation] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obs = json.loads(line)
                if uncompressed_only and obs.get("compressed"):
                    continue
                observations.append(obs)
            except json.JSONDecodeError:
                continue  # Korrupte Zeile überspringen, nicht crashen
    except OSError:
        return []

    return observations


def get_observation(
    agent_id: str,
    session_id: str,
    obs_id: str,
) -> RawObservation | None:
    """Direkter Lookup einer einzelnen Observation per ID."""
    for obs in list_raw_observations(agent_id, session_id):
        if obs.get("id") == obs_id:
            return obs
    return None


def mark_compressed(
    agent_id: str,
    session_id: str,
    obs_id: str,
    compressed_id: str,
) -> bool:
    """Markiert eine einzelne Observation als komprimiert.

    Convenience-Wrapper um `mark_compressed_bulk`. Für Schleifen über viele
    Observations IMMER bulk verwenden — Single-Calls rewriten die ganze JSONL
    pro Aufruf.
    """
    return mark_compressed_bulk(agent_id, session_id, {obs_id: compressed_id}) > 0


def mark_compressed_bulk(
    agent_id: str,
    session_id: str,
    mappings: dict[str, str],
) -> int:
    """
    Markiert mehrere Observations gleichzeitig als komprimiert.

    `mappings`: {raw_observation_id: compressed_id}

    Liest die JSONL einmal, aktualisiert alle Treffer in-memory, schreibt
    einmal atomisch (temp + rename). Bei N Observations und M Aufrufern
    spart das O(N×M) → O(N) IO-Operations gegenüber dem Single-Pattern.
    Gibt Anzahl der tatsächlich gefundenen + aktualisierten Observations zurück.
    """
    if not mappings:
        return 0
    path = _obs_file(agent_id, session_id)
    if not path.exists():
        return 0

    found = 0
    updated_lines: list[str] = []

    with _exclusive_lock(path):
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obs = json.loads(line)
                    obs_id = obs.get("id")
                    if obs_id in mappings:
                        obs["compressed"] = True
                        obs["compressed_id"] = mappings[obs_id]
                        found += 1
                    updated_lines.append(json.dumps(obs, ensure_ascii=False))
                except json.JSONDecodeError:
                    updated_lines.append(line)
        except OSError:
            return 0

        if found:
            tmp = path.with_suffix(".tmp")
            tmp.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
            tmp.replace(path)
    return found
