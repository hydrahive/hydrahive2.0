#!/usr/bin/env python3
"""Claude-Code Stop/SubagentStop-Hook: spiegelt das Transkript live ins
HydraHive-Datamining. Fail-safe — bricht nie die Claude-Code-Session ab."""
from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path

from transcript import parse_entries
from redact import redact_entries
from state import load_state, save_state

try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:  # pragma: no cover — nicht-Unix
    _HAS_FCNTL = False


@contextlib.contextmanager
def _session_lock(state_dir: Path, cc_session_id: str):
    """Serialisiert gleichzeitige Hook-Aufrufe für DIESELBE CC-Session.

    Ohne Lock rufen parallel feuernde Stop/SubagentStop-Hooks je ensure_session,
    bevor der State eine hh_session_id hält → mehrere HH-Sessions pro CC-Session
    (die beobachtete async-Race). Der Lock pro cc_session_id verhindert das
    unabhängig von der Hook-Wiring (auch Stop vs SubagentStop)."""
    if not _HAS_FCNTL:
        yield
        return
    state_dir.mkdir(parents=True, exist_ok=True)
    with open(state_dir / f"{cc_session_id}.lock", "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def run_sync(payload: dict, client, state_dir: Path, agent_id: str) -> dict:
    cc_session_id = payload.get("session_id")
    transcript_path = payload.get("transcript_path")
    if not cc_session_id or not transcript_path:
        return {"ok": False, "reason": "missing session_id/transcript_path"}
    p = Path(transcript_path)
    if not p.exists():
        return {"ok": False, "reason": "transcript not found"}

    with _session_lock(state_dir, cc_session_id):
        entries = redact_entries(parse_entries(p.read_text(errors="replace").splitlines()))
        st = load_state(state_dir, cc_session_id)

        hh_session_id = st["hh_session_id"]
        if not hh_session_id:
            hh_session_id = client.ensure_session(
                agent_id=agent_id, title=f"claude-code {cc_session_id}")

        synced_ids = list(st["synced_ids"])
        seen = set(synced_ids)
        new = [e for e in entries if e["message_id"] not in seen]
        for e in new:
            client.log(hh_session_id, e["message_id"], e["role"], e["content"], e["created_at"])
            synced_ids.append(e["message_id"])

        save_state(state_dir, cc_session_id, hh_session_id, synced_ids)
        return {"ok": True, "synced": len(new), "total": len(entries)}


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    try:
        from client import HiveClient
        # Secure-by-default: TLS-Verifikation an, außer explizit per HH_VERIFY_SSL=0
        # abgewählt. Der Payload enthält die komplette Konversation inkl. Secrets.
        verify_ssl = os.environ.get("HH_VERIFY_SSL", "1").lower() not in ("0", "false", "no")
        if not verify_ssl:
            sys.stderr.write(
                "[datamining-sync] WARNUNG: TLS-Verifikation aus (HH_VERIFY_SSL=0) — "
                "Konversation inkl. Secrets geht ungeprüft über die Leitung\n")
        hive = HiveClient(
            base_url=os.environ["HH_BASE_URL"],
            api_key=os.environ.get("HH_API_KEY"),
            user=os.environ.get("HH_USER"),
            password=os.environ.get("HH_PASS"),
            verify_ssl=verify_ssl,
        )
        state_dir = Path(os.environ.get(
            "HH_SYNC_STATE_DIR", str(Path.home() / ".claude" / "datamining-sync")))
        agent_id = os.environ.get("HH_AGENT_ID", "claude-code")
        run_sync(payload, hive, state_dir, agent_id)
    except Exception as e:  # fail-safe: Session nie blockieren
        sys.stderr.write(f"[datamining-sync] skipped: {e}\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
