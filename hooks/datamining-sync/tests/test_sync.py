import json
from pathlib import Path

from sync import run_sync


class FakeClient:
    def __init__(self):
        self.created = []
        self.logged = []

    def ensure_session(self, agent_id, title):
        self.created.append((agent_id, title))
        return "hh-session-1"

    def log(self, session_id, message_id, role, content, created_at):
        self.logged.append((session_id, message_id, role))


def _write_transcript(path: Path, n_user: int):
    lines = []
    for i in range(n_user):
        lines.append(json.dumps({"type": "user", "uuid": f"u{i}",
                                  "timestamp": "t", "message": {"role": "user", "content": f"m{i}"}}))
    path.write_text("\n".join(lines))


def test_first_run_creates_session_and_logs_all(tmp_path):
    tp = tmp_path / "t.jsonl"
    _write_transcript(tp, 3)
    client = FakeClient()
    payload = {"session_id": "cc-1", "transcript_path": str(tp)}
    res = run_sync(payload, client, tmp_path / "state", agent_id="joshua")
    assert res == {"ok": True, "synced": 3, "total": 3}
    assert client.created == [("joshua", "claude-code cc-1")]
    assert [l[1] for l in client.logged] == ["u0", "u1", "u2"]


def test_second_run_only_logs_new_and_reuses_session(tmp_path):
    tp = tmp_path / "t.jsonl"
    _write_transcript(tp, 2)
    state_dir = tmp_path / "state"
    client = FakeClient()
    payload = {"session_id": "cc-1", "transcript_path": str(tp)}
    run_sync(payload, client, state_dir, agent_id="joshua")
    _write_transcript(tp, 4)  # zwei neue Einträge
    client2 = FakeClient()
    res = run_sync(payload, client2, state_dir, agent_id="joshua")
    assert res == {"ok": True, "synced": 2, "total": 4}
    assert client2.created == []  # Session aus State wiederverwendet
    assert [l[1] for l in client2.logged] == ["u2", "u3"]


def test_missing_payload_fields_noop(tmp_path):
    client = FakeClient()
    res = run_sync({}, client, tmp_path / "state", agent_id="joshua")
    assert res["ok"] is False
    assert client.logged == []


def _write_ids(path: Path, ids):
    path.write_text("\n".join(json.dumps(
        {"type": "user", "uuid": u, "timestamp": "t", "message": {"role": "user", "content": u}}
    ) for u in ids))


def test_inserted_middle_entry_is_sent_not_skipped(tmp_path):
    """ID-Set-Robustheit: ein mitten eingefügter Eintrag wird gesendet, ein
    bereits gesehener nie erneut. Ein reiner Offset-Zähler hätte u1 übersprungen
    und u2 fälschlich erneut gesendet."""
    tp = tmp_path / "t.jsonl"
    state_dir = tmp_path / "state"
    _write_ids(tp, ["u0", "u2"])
    run_sync({"session_id": "cc-1", "transcript_path": str(tp)}, FakeClient(), state_dir, agent_id="j")

    _write_ids(tp, ["u0", "u1", "u2"])  # u1 nachträglich dazwischen
    c = FakeClient()
    run_sync({"session_id": "cc-1", "transcript_path": str(tp)}, c, state_dir, agent_id="j")
    assert [l[1] for l in c.logged] == ["u1"]


def test_redaction_applied_before_send(tmp_path):
    tp = tmp_path / "t.jsonl"
    tp.write_text(json.dumps({"type": "user", "uuid": "x", "timestamp": "t",
                              "message": {"role": "user", "content": "token=hhk_abcd1234efgh5678"}}))
    captured = []

    class CapClient(FakeClient):
        def log(self, session_id, message_id, role, content, created_at):
            captured.append(content)
            super().log(session_id, message_id, role, content, created_at)

    run_sync({"session_id": "cc-1", "transcript_path": str(tp)}, CapClient(), tmp_path / "state", agent_id="j")
    assert "hhk_abcd" not in captured[0]
