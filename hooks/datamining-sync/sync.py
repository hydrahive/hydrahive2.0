#!/usr/bin/env python3
"""Claude-Code Stop/SubagentStop-Hook: spiegelt das Transkript live ins
HydraHive-Datamining. Fail-safe — bricht nie die Claude-Code-Session ab."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from transcript import parse_entries
from state import load_state, save_state


def run_sync(payload: dict, client, state_dir: Path, agent_id: str) -> dict:
    cc_session_id = payload.get("session_id")
    transcript_path = payload.get("transcript_path")
    if not cc_session_id or not transcript_path:
        return {"ok": False, "reason": "missing session_id/transcript_path"}
    p = Path(transcript_path)
    if not p.exists():
        return {"ok": False, "reason": "transcript not found"}

    entries = parse_entries(p.read_text(errors="replace").splitlines())
    st = load_state(state_dir, cc_session_id)

    hh_session_id = st["hh_session_id"]
    if not hh_session_id:
        hh_session_id = client.ensure_session(
            agent_id=agent_id, title=f"claude-code {cc_session_id}")

    new = entries[st["synced"]:]
    for e in new:
        client.log(hh_session_id, e["message_id"], e["role"], e["content"], e["created_at"])

    save_state(state_dir, cc_session_id, hh_session_id, len(entries))
    return {"ok": True, "synced": len(new), "total": len(entries)}


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        payload = {}
    try:
        from client import HiveClient
        hive = HiveClient(
            base_url=os.environ["HH_BASE_URL"],
            api_key=os.environ.get("HH_API_KEY"),
            user=os.environ.get("HH_USER"),
            password=os.environ.get("HH_PASS"),
            verify_ssl=os.environ.get("HH_VERIFY_SSL", "0").lower() in ("1", "true", "yes"),
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
