# Datamining Live-Ingest für externe Instanzen — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Externe Claude-Code-Instanzen spiegeln ihre Konversation (inkl. Tool-Calls/-Results/Thinking) live ins HydraHive-Datamining — über denselben `messages.append() → Mirror`-Pfad wie native Agenten.

**Architecture:** Zwei Hälften. (1) HydraHive-Core bekommt einen schlanken, idempotenten Append-Endpoint `POST /api/sessions/{id}/log`, der `messages.append()` aufruft und damit den bestehenden Mirror auslöst — **kein** Agenten-Lauf (im Gegensatz zu `/inject`). (2) Ein Claude-Code-`Stop`/`SubagentStop`-Hook (außerhalb des Core) liest das Transkript-JSONL und schickt neue Einträge an den Endpoint. Idempotenz doppelt abgesichert: SQLite `INSERT OR IGNORE` auf der stabilen Transkript-UUID + PG-Mirror `ON CONFLICT (id) DO NOTHING`.

**Tech Stack:** Python 3.12 / FastAPI / SQLite (Core), pytest (Tests), Python+httpx (Hook). Keine neuen Dependencies im Core.

**Wichtig — Deployment:** Claude baut + testet nur lokal (`pytest`). **Till deployt** auf Test-/Prod-Server und installiert den Hook. Kein Prod-Zugriff durch Claude.

---

## Prerequisites — einmaliges Setup (führt Till aus, kein Code-Task)

Eine externe Instanz wird als **Agent** + eigener **User** modelliert. Beides einmalig pro Instanz anlegen (Beispiel „joshua", gegen den Zielserver):

```bash
# 1. User "joshua" (admin-only Endpoint, du bist als admin eingeloggt)
curl -sk -X POST "$HH/api/users" -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"username":"joshua","password":"<pw>","role":"user"}'

# 2. Agent "joshua" (admin-only)
curl -sk -X POST "$HH/api/agents" -H "Authorization: Bearer $ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"joshua","name":"Joshua (Claude Code)","type":"master","llm_model":"claude-opus-4-8","tools":[]}'
```

> Der genaue Body von `POST /api/agents` ist beim Bau gegen `routes/agents.py` (`AgentCreate`-Model) zu prüfen — Felder können abweichen. Dieser Schritt ist **Voraussetzung**, kein Teil der getesteten Tasks.

---

## File Structure

**Core (HydraHive-Repo):**
- Modify: `core/src/hydrahive/db/messages.py` — `append()` bekommt optionale `message_id` + `created_at`, Insert wird idempotent.
- Modify: `core/src/hydrahive/api/routes/sessions_messages.py` — neues Pydantic-Model `LogIngestBody` + Route `POST /{session_id}/log`.
- Test: `core/tests/test_messages_append_idempotent.py`
- Test: `core/tests/test_session_log_ingest.py`

**Hook (HydraHive-Repo, außerhalb `core/`):**
- Create: `hooks/datamining-sync/transcript.py` — reine Transkript-JSONL→Message-Dict-Konvertierung.
- Create: `hooks/datamining-sync/state.py` — Sidecar-State (hh_session_id + Offset), atomar.
- Create: `hooks/datamining-sync/client.py` — dünner sync-httpx-Client (Login/Session/Log).
- Create: `hooks/datamining-sync/sync.py` — Orchestrator + stdin-Entry-Point (fail-safe).
- Create: `hooks/datamining-sync/tests/conftest.py` — sys.path-Fix.
- Create: `hooks/datamining-sync/tests/test_transcript.py`
- Create: `hooks/datamining-sync/tests/test_state.py`
- Create: `hooks/datamining-sync/tests/test_sync.py`
- Create: `hooks/datamining-sync/README.md` — settings.json-Verdrahtung.

---

## Phase A — Core-Endpoint

### Task 1: `messages.append()` idempotent machen

**Files:**
- Modify: `core/src/hydrahive/db/messages.py:13-47`
- Test: `core/tests/test_messages_append_idempotent.py`

- [ ] **Step 1: Failing-Test schreiben**

```python
# core/tests/test_messages_append_idempotent.py
from __future__ import annotations

import pytest

from hydrahive.db import messages as messages_db


@pytest.fixture
def session_id(client, auth_headers):
    r = client.post("/api/sessions", json={"agent_id": "test-agent-001"}, headers=auth_headers)
    assert r.status_code == 201
    return r.json()["id"]


def test_append_with_explicit_id_is_idempotent(session_id):
    m1 = messages_db.append(session_id, "user", "hallo", message_id="fixed-1")
    m2 = messages_db.append(session_id, "user", "hallo", message_id="fixed-1")
    assert m1.id == "fixed-1"
    assert m2.id == "fixed-1"
    msgs = messages_db.list_for_session(session_id)
    assert len([m for m in msgs if m.id == "fixed-1"]) == 1


def test_append_without_id_generates_unique_ids(session_id):
    a = messages_db.append(session_id, "user", "eins")
    b = messages_db.append(session_id, "user", "zwei")
    assert a.id != b.id
    ids = {m.id for m in messages_db.list_for_session(session_id)}
    assert {a.id, b.id} <= ids


def test_append_honours_explicit_created_at(session_id):
    m = messages_db.append(session_id, "user", "x", message_id="ts-1",
                           created_at="2025-11-01T08:00:00Z")
    assert m.created_at == "2025-11-01T08:00:00Z"
    got = messages_db.get("ts-1")
    assert got is not None and got.created_at == "2025-11-01T08:00:00Z"
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd core && python3 -m pytest tests/test_messages_append_idempotent.py -v`
Expected: FAIL — `append() got an unexpected keyword argument 'message_id'`

- [ ] **Step 3: `append()` anpassen**

Ersetze die Funktion `append` (Z. 13-47) vollständig durch:

```python
def append(
    session_id: str,
    role: str,
    content: Any,
    token_count: int | None = None,
    metadata: dict | None = None,
    message_id: str | None = None,
    created_at: str | None = None,
) -> Message:
    m = Message(
        id=message_id or uuid7(),
        session_id=session_id,
        role=role,
        content=content,
        created_at=created_at or now_iso(),
        token_count=token_count,
        metadata=metadata or {},
    )
    content_str = content if isinstance(content, str) else json.dumps(content)
    with db() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO messages
               (id, session_id, role, content, created_at, token_count, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (m.id, m.session_id, m.role, content_str, m.created_at,
             m.token_count,
             json.dumps(m.metadata) if m.metadata else None),
        )
        inserted = cur.rowcount > 0
        if inserted:
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (m.created_at, session_id),
            )
    if inserted:
        from hydrahive.db import sessions as sessions_db
        s = sessions_db.get(session_id)
        if s:
            mirror.schedule_message(m, s)
    return m
```

Begründung: Für bestehende Aufrufer (frische `uuid7`) ist `inserted` immer `True` → Verhalten identisch. Nur bei doppelt geliefertem `message_id` greift `IGNORE`, und der Mirror feuert dann **nicht** erneut.

- [ ] **Step 4: Test laufen lassen, PASS bestätigen**

Run: `cd core && python3 -m pytest tests/test_messages_append_idempotent.py -v`
Expected: PASS (3 Tests)

- [ ] **Step 5: Regression — Gesamtsuite grün halten**

Run: `cd core && python3 -m pytest -q`
Expected: PASS (keine bestehenden Tests gebrochen — `append`-Verhalten für Alt-Aufrufer unverändert)

- [ ] **Step 6: Commit**

```bash
git add core/src/hydrahive/db/messages.py core/tests/test_messages_append_idempotent.py
git commit -m "feat(db): messages.append idempotent per message_id + created_at-Override"
```

---

### Task 2: Endpoint `POST /api/sessions/{id}/log`

**Files:**
- Modify: `core/src/hydrahive/api/routes/sessions_messages.py` (Model + Route am Dateiende anhängen, vor `inject_message` oder danach — Reihenfolge egal)
- Test: `core/tests/test_session_log_ingest.py`

- [ ] **Step 1: Failing-Test schreiben**

```python
# core/tests/test_session_log_ingest.py
from __future__ import annotations

import pytest

from tests.conftest import error_code


@pytest.fixture
def session_id(client, auth_headers):
    r = client.post("/api/sessions", json={"agent_id": "test-agent-001"}, headers=auth_headers)
    assert r.status_code == 201
    return r.json()["id"]


def test_owner_can_log_text_message(client, auth_headers, session_id):
    r = client.post(f"/api/sessions/{session_id}/log",
                    json={"role": "user", "content": "hallo welt", "message_id": "u-1"},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "message_id": "u-1"}
    msgs = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers).json()
    assert any(m["id"] == "u-1" and m["content"] == "hallo welt" for m in msgs)


def test_log_is_idempotent(client, auth_headers, session_id):
    body = {"role": "user", "content": "doppelt", "message_id": "dup-1"}
    client.post(f"/api/sessions/{session_id}/log", json=body, headers=auth_headers)
    client.post(f"/api/sessions/{session_id}/log", json=body, headers=auth_headers)
    msgs = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers).json()
    assert len([m for m in msgs if m["id"] == "dup-1"]) == 1


def test_log_accepts_assistant_block_content(client, auth_headers, session_id):
    blocks = [
        {"type": "text", "text": "ich rufe ein tool"},
        {"type": "tool_use", "id": "tu_1", "name": "Bash", "input": {"command": "ls"}},
    ]
    r = client.post(f"/api/sessions/{session_id}/log",
                    json={"role": "assistant", "content": blocks, "message_id": "a-1"},
                    headers=auth_headers)
    assert r.status_code == 200, r.text
    msgs = client.get(f"/api/sessions/{session_id}/messages", headers=auth_headers).json()
    logged = next(m for m in msgs if m["id"] == "a-1")
    assert logged["content"][1]["name"] == "Bash"


def test_log_unknown_session_404(client, auth_headers):
    r = client.post("/api/sessions/does-not-exist/log",
                    json={"role": "user", "content": "x"}, headers=auth_headers)
    assert r.status_code == 404
    assert error_code(r) == "session_not_found"


def test_log_non_owner_403(client, auth_headers, admin_headers):
    # Session gehört admin; testuser darf nicht loggen
    r = client.post("/api/sessions", json={"agent_id": "test-agent-001"}, headers=admin_headers)
    admin_sid = r.json()["id"]
    r = client.post(f"/api/sessions/{admin_sid}/log",
                    json={"role": "user", "content": "fremd"}, headers=auth_headers)
    assert r.status_code == 403
    assert error_code(r) == "session_no_access"


def test_log_invalid_role_422(client, auth_headers, session_id):
    r = client.post(f"/api/sessions/{session_id}/log",
                    json={"role": "system", "content": "nope"}, headers=auth_headers)
    assert r.status_code == 422
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd core && python3 -m pytest tests/test_session_log_ingest.py -v`
Expected: FAIL — 404/405 (Route existiert nicht)

- [ ] **Step 3: Model + Route ergänzen**

In `core/src/hydrahive/api/routes/sessions_messages.py` `Field`-Import sicherstellen (bereits vorhanden via `from pydantic import BaseModel, Field`), dann am Dateiende anhängen:

```python
class LogIngestBody(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str | list
    message_id: str | None = None
    token_count: int | None = None
    created_at: str | None = None
    metadata: dict | None = None


@messages_router.post("/{session_id}/log")
def log_ingest(
    session_id: str,
    body: LogIngestBody,
    auth: Annotated[tuple[str, str], Depends(require_auth)],
) -> dict:
    """Externer Live-Ingest: hängt eine Message an und löst den Mirror aus.

    Reines Mitschreiben — kein Agenten-Lauf (vgl. /inject). Idempotent über
    body.message_id (INSERT OR IGNORE). Für externe Claude-Code-Instanzen, die
    ihre Konversation ins Datamining spiegeln.
    """
    s = sessions_db.get(session_id)
    if not s:
        raise coded(status.HTTP_404_NOT_FOUND, "session_not_found")
    check_owner(s, *auth)
    m = messages_db.append(
        session_id,
        body.role,
        body.content,
        token_count=body.token_count,
        metadata=body.metadata,
        message_id=body.message_id,
        created_at=body.created_at,
    )
    return {"ok": True, "message_id": m.id}
```

- [ ] **Step 4: Test laufen lassen, PASS bestätigen**

Run: `cd core && python3 -m pytest tests/test_session_log_ingest.py -v`
Expected: PASS (6 Tests)

- [ ] **Step 5: Gesamtsuite**

Run: `cd core && python3 -m pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add core/src/hydrahive/api/routes/sessions_messages.py core/tests/test_session_log_ingest.py
git commit -m "feat(api): POST /sessions/{id}/log — idempotenter Datamining-Ingest ohne Agenten-Lauf"
```

---

## Phase B — Claude-Code-Hook

### Task 3: Transkript-Parser (rein)

**Files:**
- Create: `hooks/datamining-sync/transcript.py`
- Create: `hooks/datamining-sync/tests/conftest.py`
- Create: `hooks/datamining-sync/tests/test_transcript.py`

- [ ] **Step 1: sys.path-conftest schreiben**

```python
# hooks/datamining-sync/tests/conftest.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

- [ ] **Step 2: Failing-Test schreiben**

```python
# hooks/datamining-sync/tests/test_transcript.py
import json

from transcript import parse_entries


def _line(**kw):
    return json.dumps(kw)


def test_extracts_user_and_assistant_only():
    lines = [
        _line(type="user", uuid="u1", timestamp="2026-05-29T10:00:00Z",
              message={"role": "user", "content": "hallo"}),
        _line(type="assistant", uuid="a1", timestamp="2026-05-29T10:00:01Z",
              message={"role": "assistant", "content": [{"type": "text", "text": "hi"}]}),
        _line(type="system", uuid="s1", message={"role": "system", "content": "x"}),
        _line(type="file-history-snapshot", uuid="f1"),
        "   ",
        "{not valid json",
    ]
    out = parse_entries(lines)
    assert [e["message_id"] for e in out] == ["u1", "a1"]
    assert out[0] == {"message_id": "u1", "role": "user",
                      "content": "hallo", "created_at": "2026-05-29T10:00:00Z"}
    assert out[1]["content"][0]["text"] == "hi"


def test_skips_entries_without_uuid_or_content():
    lines = [
        _line(type="user", timestamp="t", message={"role": "user", "content": "no uuid"}),
        _line(type="assistant", uuid="a2", message={"role": "assistant"}),  # kein content
    ]
    assert parse_entries(lines) == []
```

- [ ] **Step 3: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd hooks/datamining-sync && python3 -m pytest tests/test_transcript.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'transcript'`

- [ ] **Step 4: `transcript.py` schreiben**

```python
# hooks/datamining-sync/transcript.py
"""Claude-Code-Transkript-JSONL → mirror-fähige Message-Dicts (reine Funktion)."""
from __future__ import annotations

import json


def parse_entries(lines: list[str]) -> list[dict]:
    """Filtert auf user/assistant-Einträge mit message.role+content.

    Andere Entry-Typen (system, attachment, file-history-snapshot, ai-title,
    last-prompt, permission-mode) werden übersprungen. Jeder Treffer:
    {message_id, role, content, created_at}. message_id = stabile Transkript-UUID.
    """
    out: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") not in ("user", "assistant"):
            continue
        msg = e.get("message")
        uuid = e.get("uuid")
        if not isinstance(msg, dict) or not uuid:
            continue
        role = msg.get("role")
        content = msg.get("content")
        if role not in ("user", "assistant") or content is None:
            continue
        out.append({
            "message_id": uuid,
            "role": role,
            "content": content,
            "created_at": e.get("timestamp"),
        })
    return out
```

- [ ] **Step 5: Test laufen lassen, PASS bestätigen**

Run: `cd hooks/datamining-sync && python3 -m pytest tests/test_transcript.py -v`
Expected: PASS (2 Tests)

- [ ] **Step 6: Commit**

```bash
git add hooks/datamining-sync/transcript.py hooks/datamining-sync/tests/
git commit -m "feat(hook): Transkript-JSONL-Parser für Datamining-Sync"
```

---

### Task 4: Sidecar-State + Offset

**Files:**
- Create: `hooks/datamining-sync/state.py`
- Create: `hooks/datamining-sync/tests/test_state.py`

- [ ] **Step 1: Failing-Test schreiben**

```python
# hooks/datamining-sync/tests/test_state.py
from pathlib import Path

from state import load_state, save_state


def test_load_missing_returns_defaults(tmp_path):
    assert load_state(tmp_path, "cc-1") == {"hh_session_id": None, "synced": 0}


def test_save_then_load_roundtrips(tmp_path):
    save_state(tmp_path, "cc-1", "hh-abc", 7)
    assert load_state(tmp_path, "cc-1") == {"hh_session_id": "hh-abc", "synced": 7}


def test_corrupt_file_returns_defaults(tmp_path):
    (tmp_path / "cc-2.json").write_text("{garbage")
    assert load_state(tmp_path, "cc-2") == {"hh_session_id": None, "synced": 0}
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd hooks/datamining-sync && python3 -m pytest tests/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'state'`

- [ ] **Step 3: `state.py` schreiben**

```python
# hooks/datamining-sync/state.py
"""Pro-CC-Session Sidecar-State: hh_session_id + Sync-Offset. Atomarer Write."""
from __future__ import annotations

import json
from pathlib import Path

_DEFAULT = {"hh_session_id": None, "synced": 0}


def _path(state_dir: Path, cc_session_id: str) -> Path:
    return state_dir / f"{cc_session_id}.json"


def load_state(state_dir: Path, cc_session_id: str) -> dict:
    p = _path(state_dir, cc_session_id)
    if not p.exists():
        return dict(_DEFAULT)
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return dict(_DEFAULT)
    return {"hh_session_id": data.get("hh_session_id"), "synced": int(data.get("synced", 0))}


def save_state(state_dir: Path, cc_session_id: str, hh_session_id: str, synced: int) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    p = _path(state_dir, cc_session_id)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps({"hh_session_id": hh_session_id, "synced": synced}))
    tmp.replace(p)
```

- [ ] **Step 4: Test laufen lassen, PASS bestätigen**

Run: `cd hooks/datamining-sync && python3 -m pytest tests/test_state.py -v`
Expected: PASS (3 Tests)

- [ ] **Step 5: Commit**

```bash
git add hooks/datamining-sync/state.py hooks/datamining-sync/tests/test_state.py
git commit -m "feat(hook): atomarer Sidecar-State für Datamining-Sync-Offset"
```

---

### Task 5: REST-Client (sync httpx)

**Files:**
- Create: `hooks/datamining-sync/client.py`

Kein eigener Unit-Test (dünner I/O-Wrapper; wird in Task 6 über den Orchestrator-Test mit Fake-Client abgedeckt). Interface bewusst klein, damit der Orchestrator einen Fake injizieren kann.

- [ ] **Step 1: `client.py` schreiben**

```python
# hooks/datamining-sync/client.py
"""Dünner synchroner HydraHive-REST-Client für den Sync-Hook.

Auth: HH_API_KEY (Bearer) ODER HH_USER/HH_PASS (Login). Bewusst minimal —
Orchestrator-Tests injizieren einen Fake mit denselben Methoden.
"""
from __future__ import annotations

import httpx


class HiveClient:
    def __init__(self, base_url: str, api_key: str | None = None,
                 user: str | None = None, password: str | None = None,
                 verify_ssl: bool = False, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.user = user
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._token: str | None = api_key

    def _login(self) -> None:
        r = httpx.post(f"{self.base_url}/api/auth/login",
                       json={"username": self.user, "password": self.password},
                       timeout=self.timeout, verify=self.verify_ssl)
        r.raise_for_status()
        self._token = r.json()["access_token"]

    def _headers(self) -> dict:
        if not self._token and self.user:
            self._login()
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def ensure_session(self, agent_id: str, title: str) -> str:
        r = httpx.post(f"{self.base_url}/api/sessions",
                       json={"agent_id": agent_id, "title": title},
                       headers=self._headers(), timeout=self.timeout, verify=self.verify_ssl)
        r.raise_for_status()
        return r.json()["id"]

    def log(self, session_id: str, message_id: str, role: str,
            content, created_at: str | None) -> None:
        r = httpx.post(f"{self.base_url}/api/sessions/{session_id}/log",
                       json={"message_id": message_id, "role": role,
                             "content": content, "created_at": created_at},
                       headers=self._headers(), timeout=self.timeout, verify=self.verify_ssl)
        r.raise_for_status()
```

- [ ] **Step 2: Import-Smoke (kein Netzwerk)**

Run: `cd hooks/datamining-sync && python3 -c "import client; print('ok')"`
Expected: `ok` (httpx muss vorhanden sein; falls nicht: `pip install httpx`)

- [ ] **Step 3: Commit**

```bash
git add hooks/datamining-sync/client.py
git commit -m "feat(hook): dünner sync-REST-Client (Login/Session/Log)"
```

---

### Task 6: Orchestrator + Entry-Point + README

**Files:**
- Create: `hooks/datamining-sync/sync.py`
- Create: `hooks/datamining-sync/tests/test_sync.py`
- Create: `hooks/datamining-sync/README.md`

- [ ] **Step 1: Failing-Test schreiben**

```python
# hooks/datamining-sync/tests/test_sync.py
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
```

- [ ] **Step 2: Test laufen lassen, Fehlschlag bestätigen**

Run: `cd hooks/datamining-sync && python3 -m pytest tests/test_sync.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'sync'`

- [ ] **Step 3: `sync.py` schreiben**

```python
# hooks/datamining-sync/sync.py
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
```

- [ ] **Step 4: Test laufen lassen, PASS bestätigen**

Run: `cd hooks/datamining-sync && python3 -m pytest tests/test_sync.py -v`
Expected: PASS (3 Tests)

- [ ] **Step 5: Gesamte Hook-Suite**

Run: `cd hooks/datamining-sync && python3 -m pytest -q`
Expected: PASS (8 Tests)

- [ ] **Step 6: README schreiben**

```markdown
# hooks/datamining-sync/README.md
# Datamining-Sync-Hook

Spiegelt jede Claude-Code-Runde (User, Assistant, Tool-Calls, Tool-Results,
Thinking) live ins HydraHive-Datamining — via `POST /api/sessions/{id}/log`.

## Voraussetzungen (auf dem HydraHive-Server, einmalig)
- User + Agent für diese Instanz angelegt (siehe Implementierungsplan, Prerequisites).
- `HH_PG_MIRROR_DSN` gesetzt (sonst landet nichts im Datamining).

## Verdrahtung in `~/.claude/settings.json`

    {
      "hooks": {
        "Stop": [{
          "command": "python3 /PFAD/zu/hooks/datamining-sync/sync.py"
        }],
        "SubagentStop": [{
          "command": "python3 /PFAD/zu/hooks/datamining-sync/sync.py"
        }]
      }
    }

## Env-Variablen (im Hook-Prozess verfügbar machen)

| Variable | Pflicht | Beispiel |
|---|---|---|
| `HH_BASE_URL` | ja | `https://192.168.3.22` |
| `HH_API_KEY` | wenn kein User/Pass | `hhk_...` |
| `HH_USER` / `HH_PASS` | wenn kein Key | `joshua` / `...` |
| `HH_AGENT_ID` | nein (default `claude-code`) | `joshua` |
| `HH_VERIFY_SSL` | nein (default `0`) | `0` |
| `HH_SYNC_STATE_DIR` | nein | `~/.claude/datamining-sync` |

Da Hook-Commands die Umgebung des Claude-Code-Prozesses erben, die `HH_*`-Vars
beim Start setzen (Shell-Profil / Wrapper-Skript), das `sync.py` aufruft.

## Eigenschaften
- **Idempotent:** stabile Transkript-UUID + `INSERT OR IGNORE` → keine Duplikate.
- **Fail-safe:** HydraHive nicht erreichbar → Fehler auf stderr, Session läuft weiter.
- **Offset:** pro CC-Session in `HH_SYNC_STATE_DIR/<session>.json`.

## Secrets-Hinweis
Es wird **alles** gespiegelt — auch Passwörter/Keys, die in eine Session getippt
werden. Optionale Redaction (z.B. `hhk_`/`Bearer`/`HH_PASS`-Muster maskieren)
gehört clientseitig in `transcript.py` und ist hier bewusst noch nicht enthalten.
```

- [ ] **Step 7: Commit**

```bash
git add hooks/datamining-sync/sync.py hooks/datamining-sync/tests/test_sync.py hooks/datamining-sync/README.md
git commit -m "feat(hook): Orchestrator + Entry-Point + README für Datamining-Sync"
```

---

## Manuelle Verifikation (Till, nach Deploy)

1. User+Agent „joshua" auf dem Testserver anlegen (Prerequisites).
2. Hook in `~/.claude/settings.json` einer Test-Instanz verdrahten, `HH_*`-Env setzen.
3. In der Instanz eine kurze Unterhaltung führen (inkl. einem Tool-Call).
4. Im Datamining-Frontend prüfen: Session unter Agent `joshua` sichtbar, Events
   `user_input` / `assistant_text` / `tool_call` / `tool_result` vorhanden.
5. Hook erneut feuern (zweite Runde) → keine Duplikate, nur neue Events.

---

## Self-Review

**Spec-Coverage (gegen SPEC.md „Externe Instanzen (Live-Ingest)"):**
- „über messages.append() → Mirror" → Task 2 ruft `messages.append`, Mirror feuert unverändert. ✓
- „POST /api/sessions/{id}/log (require_auth, Owner-Check), kein Agenten-Lauf" → Task 2. ✓
- „Idempotenz: stabile Message-ID, INSERT OR IGNORE" → Task 1 + Task 2-Test `test_log_is_idempotent`. ✓
- „Instanz = registrierter Agent + eigener Login-User" → Prerequisites. ✓
- „Stop-Hook in ~/.claude/, liest Transkript, außerhalb Core" → Phase B, `hooks/`. ✓
- „Erfasst alles, opt-in pro Instanz" → Hook erfasst user+assistant inkl. Tool-Blöcke; opt-in über settings.json-Eintrag. ✓
- „Keine Redaction im Core — clientseitig" → README-Hinweis, bewusst nicht implementiert (YAGNI bis gewünscht). ✓

**Platzhalter:** keine — jeder Code-Step enthält vollständigen Code.

**Typ-Konsistenz:** `append(..., message_id, created_at)` (Task 1) == Aufruf in `log_ingest` (Task 2). `run_sync(payload, client, state_dir, agent_id)`-Signatur identisch in Test (Task 6) und Implementierung. `HiveClient.ensure_session/log`-Signaturen == FakeClient im Test.

**Bewusste Scope-Grenzen (YAGNI):** keine Redaction, keine Erfassung von `attachment`/`system`-Entries, kein Retry im Hook (fail-safe statt robust-queue) — alles nachrüstbar, nichts davon von der SPEC verlangt.
