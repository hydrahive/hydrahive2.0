# HydraHive API MCP-Server — Implementierungsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Einen FastMCP-Server bauen der Claude Code als vollwertigen internen Agenten in HydraHive einbindet — REST-API-Zugriff auf Sessions, Agenten, Workspace, Datamining + bidirektionale AgentLink-WebSocket-Integration.

**Architecture:** Ein Python-Prozess mit FastMCP für Tool-Calls und einem asyncio-Hintergrund-Task für die AgentLink-WebSocket-Verbindung. Eingehende Handoffs landen in einer asyncio.Queue, Tools lesen daraus. Auth via User/Pass (JWT mit Auto-Refresh) oder API-Key.

**Tech Stack:** Python 3.12, FastMCP (`mcp`), httpx (async HTTP), websockets, pytest + pytest-asyncio + respx (HTTP-Mocking)

**Spec:** `docs/superpowers/specs/2026-05-15-hydrahive-mcp-design.md`

---

## Dateistruktur

```
mcp-servers/hydrahive-api/
├── server.py            # FastMCP-Instanz + Startup/Shutdown
├── _auth.py             # Login, Token-Cache, API-Key-Modus
├── _rest.py             # Async REST-Client (alle HH-API-Calls)
├── _agentlink.py        # WebSocket-Verbindung + asyncio.Queue
├── tools/
│   ├── __init__.py
│   ├── system.py        # hh_status, hh_token_stats
│   ├── sessions.py      # hh_list_sessions, hh_get_session, hh_get_messages, hh_send_message
│   ├── agents.py        # hh_list_agents, hh_get_agent, hh_update_agent
│   ├── workspace.py     # hh_list_projects, hh_list_files, hh_read_file
│   ├── datamining.py    # hh_dm_search, hh_dm_get_session, hh_dm_list_sessions, hh_dm_stats
│   └── agentlink.py     # hh_al_status, hh_al_send, hh_al_check_inbox, hh_al_reply
├── tests/
│   ├── conftest.py      # Fixtures: mock-REST-Client, mock-Queue
│   ├── test_auth.py
│   ├── test_rest.py
│   ├── test_tools_system.py
│   ├── test_tools_sessions.py
│   ├── test_tools_agents.py
│   ├── test_tools_workspace.py
│   ├── test_tools_datamining.py
│   └── test_agentlink.py
└── pyproject.toml
```

---

## Task 1: Projektgerüst + pyproject.toml

**Files:**
- Create: `mcp-servers/hydrahive-api/pyproject.toml`
- Create: `mcp-servers/hydrahive-api/tools/__init__.py`
- Create: `mcp-servers/hydrahive-api/tests/conftest.py`

- [ ] **Schritt 1: pyproject.toml anlegen**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "hydrahive-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "mcp[cli]>=1.0",
    "httpx>=0.27",
    "websockets>=13",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "respx>=0.21",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Schritt 2: Verzeichnisstruktur anlegen**

```bash
mkdir -p mcp-servers/hydrahive-api/tools mcp-servers/hydrahive-api/tests
touch mcp-servers/hydrahive-api/tools/__init__.py
touch mcp-servers/hydrahive-api/tests/__init__.py
```

- [ ] **Schritt 3: conftest.py anlegen**

```python
# mcp-servers/hydrahive-api/tests/conftest.py
import asyncio
import pytest

@pytest.fixture
def base_url() -> str:
    return "https://192.168.3.22"

@pytest.fixture
def token() -> str:
    return "test-jwt-token"
```

- [ ] **Schritt 4: Dependencies installieren**

```bash
cd mcp-servers/hydrahive-api
pip install -e ".[dev]"
```

- [ ] **Schritt 5: Commit**

```bash
git add mcp-servers/hydrahive-api/
git commit -m "feat(mcp): Projektgerüst hydrahive-api MCP-Server"
```

---

## Task 2: Auth-Modul (`_auth.py`)

**Files:**
- Create: `mcp-servers/hydrahive-api/_auth.py`
- Create: `mcp-servers/hydrahive-api/tests/test_auth.py`

- [ ] **Schritt 1: Failing test schreiben**

```python
# tests/test_auth.py
import pytest
import respx
import httpx
from _auth import Auth

@pytest.mark.asyncio
async def test_login_setzt_token(base_url):
    with respx.mock:
        respx.post(f"{base_url}/api/auth/login").mock(
            return_value=httpx.Response(200, json={"access_token": "jwt-abc", "token_type": "bearer"})
        )
        auth = Auth(base_url=base_url, user="admin", password="secret")
        await auth.ensure_token()
        assert auth.token == "jwt-abc"

@pytest.mark.asyncio
async def test_api_key_braucht_kein_login(base_url):
    auth = Auth(base_url=base_url, api_key="hhk_test123")
    await auth.ensure_token()   # kein HTTP-Call
    assert auth.token == "hhk_test123"

@pytest.mark.asyncio
async def test_headers_enthalten_bearer(base_url):
    auth = Auth(base_url=base_url, api_key="hhk_abc")
    await auth.ensure_token()
    assert auth.headers() == {"Authorization": "Bearer hhk_abc"}
```

- [ ] **Schritt 2: Test ausführen — muss FAIL**

```bash
cd mcp-servers/hydrahive-api && pytest tests/test_auth.py -v
```

Erwartet: `ModuleNotFoundError: No module named '_auth'`

- [ ] **Schritt 3: `_auth.py` implementieren**

```python
# mcp-servers/hydrahive-api/_auth.py
from __future__ import annotations
import os
import httpx

class Auth:
    def __init__(
        self,
        base_url: str = "",
        user: str = "",
        password: str = "",
        api_key: str = "",
        verify_ssl: bool = False,
    ):
        self.base_url = base_url or os.environ.get("HH_BASE_URL", "").rstrip("/")
        self.user = user or os.environ.get("HH_USER", "")
        self.password = password or os.environ.get("HH_PASS", "")
        self.api_key = api_key or os.environ.get("HH_API_KEY", "")
        self.verify_ssl = verify_ssl or os.environ.get("HH_VERIFY_SSL", "0") not in ("0", "false", "no")
        self.token: str = self.api_key

    async def ensure_token(self) -> None:
        if self.token:
            return
        if not self.user:
            raise RuntimeError("Kein HH_API_KEY und kein HH_USER/HH_PASS gesetzt")
        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            r = await client.post(
                f"{self.base_url}/api/auth/login",
                json={"username": self.user, "password": self.password},
                timeout=10,
            )
            r.raise_for_status()
            self.token = r.json()["access_token"]

    async def refresh(self) -> None:
        self.token = ""
        await self.ensure_token()

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}
```

- [ ] **Schritt 4: Tests grün**

```bash
pytest tests/test_auth.py -v
```

Erwartet: 3 PASSED

- [ ] **Schritt 5: Commit**

```bash
git add mcp-servers/hydrahive-api/_auth.py mcp-servers/hydrahive-api/tests/test_auth.py
git commit -m "feat(mcp): Auth-Modul — JWT-Login + API-Key"
```

---

## Task 3: REST-Client (`_rest.py`)

**Files:**
- Create: `mcp-servers/hydrahive-api/_rest.py`
- Create: `mcp-servers/hydrahive-api/tests/test_rest.py`

- [ ] **Schritt 1: Failing tests schreiben**

```python
# tests/test_rest.py
import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient

@pytest.mark.asyncio
async def test_get_ruft_korrekte_url(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )
        auth = Auth(base_url=base_url, api_key=token)
        await auth.ensure_token()
        client = RestClient(auth)
        result = await client.get("/api/health")
        assert result["status"] == "ok"

@pytest.mark.asyncio
async def test_401_triggert_refresh_und_retry(base_url):
    with respx.mock:
        respx.post(f"{base_url}/api/auth/login").mock(
            return_value=httpx.Response(200, json={"access_token": "new-token", "token_type": "bearer"})
        )
        call_count = 0
        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return httpx.Response(401)
            return httpx.Response(200, json={"ok": True})
        respx.get(f"{base_url}/api/health").mock(side_effect=side_effect)

        auth = Auth(base_url=base_url, user="admin", password="secret")
        auth.token = "old-expired-token"
        client = RestClient(auth)
        result = await client.get("/api/health")
        assert result["ok"] is True
        assert auth.token == "new-token"
```

- [ ] **Schritt 2: Test ausführen — muss FAIL**

```bash
pytest tests/test_rest.py -v
```

Erwartet: `ModuleNotFoundError: No module named '_rest'`

- [ ] **Schritt 3: `_rest.py` implementieren**

```python
# mcp-servers/hydrahive-api/_rest.py
from __future__ import annotations
from typing import Any
import httpx
from _auth import Auth

class RestClient:
    def __init__(self, auth: Auth):
        self.auth = auth

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(verify=self.auth.verify_ssl, timeout=15.0)

    async def get(self, path: str, params: dict | None = None) -> Any:
        await self.auth.ensure_token()
        url = self.auth.base_url + path
        async with self._client() as c:
            r = await c.get(url, params=params, headers=self.auth.headers())
            if r.status_code == 401:
                await self.auth.refresh()
                r = await c.get(url, params=params, headers=self.auth.headers())
            r.raise_for_status()
            return r.json()

    async def post(self, path: str, body: dict | None = None) -> Any:
        await self.auth.ensure_token()
        url = self.auth.base_url + path
        async with self._client() as c:
            r = await c.post(url, json=body, headers=self.auth.headers())
            if r.status_code == 401:
                await self.auth.refresh()
                r = await c.post(url, json=body, headers=self.auth.headers())
            r.raise_for_status()
            return r.json() if r.content else {}

    async def patch(self, path: str, body: dict) -> Any:
        await self.auth.ensure_token()
        url = self.auth.base_url + path
        async with self._client() as c:
            r = await c.patch(url, json=body, headers=self.auth.headers())
            if r.status_code == 401:
                await self.auth.refresh()
                r = await c.patch(url, json=body, headers=self.auth.headers())
            r.raise_for_status()
            return r.json()
```

- [ ] **Schritt 4: Tests grün**

```bash
pytest tests/test_rest.py -v
```

Erwartet: 2 PASSED

- [ ] **Schritt 5: Commit**

```bash
git add mcp-servers/hydrahive-api/_rest.py mcp-servers/hydrahive-api/tests/test_rest.py
git commit -m "feat(mcp): REST-Client mit Auth-Header + 401-Retry"
```

---

## Task 4: System-Tools (`tools/system.py`)

**Files:**
- Create: `mcp-servers/hydrahive-api/tools/system.py`
- Create: `mcp-servers/hydrahive-api/tests/test_tools_system.py`

- [ ] **Schritt 1: Failing tests**

```python
# tests/test_tools_system.py
import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from tools.system import get_status, get_token_stats

@pytest.mark.asyncio
async def test_get_status_gibt_health_zurueck(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/health").mock(
            return_value=httpx.Response(200, json={
                "status": "healthy", "version": "2.1.0", "uptime_s": 3600
            })
        )
        auth = Auth(base_url=base_url, api_key=token)
        client = RestClient(auth)
        result = await get_status(client)
        assert result["status"] == "healthy"
        assert result["version"] == "2.1.0"

@pytest.mark.asyncio
async def test_get_token_stats_gibt_statistiken(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/dashboard").mock(
            return_value=httpx.Response(200, json={
                "total_tokens": 1000000,
                "total_cost_usd": 12.50,
                "sessions_today": 5,
            })
        )
        auth = Auth(base_url=base_url, api_key=token)
        client = RestClient(auth)
        result = await get_token_stats(client)
        assert result["total_cost_usd"] == 12.50
```

- [ ] **Schritt 2: Test ausführen — muss FAIL**

```bash
pytest tests/test_tools_system.py -v
```

- [ ] **Schritt 3: `tools/system.py` implementieren**

```python
# mcp-servers/hydrahive-api/tools/system.py
from __future__ import annotations
from typing import Any
from _rest import RestClient

async def get_status(client: RestClient) -> dict[str, Any]:
    try:
        return await client.get("/api/health")
    except Exception as e:
        return {"error": str(e), "code": "health_failed"}

async def get_token_stats(client: RestClient) -> dict[str, Any]:
    try:
        return await client.get("/api/dashboard")
    except Exception as e:
        return {"error": str(e), "code": "stats_failed"}
```

- [ ] **Schritt 4: Tests grün**

```bash
pytest tests/test_tools_system.py -v
```

- [ ] **Schritt 5: Commit**

```bash
git add mcp-servers/hydrahive-api/tools/system.py mcp-servers/hydrahive-api/tests/test_tools_system.py
git commit -m "feat(mcp): System-Tools — hh_status, hh_token_stats"
```

---

## Task 5: Sessions-Tools (`tools/sessions.py`)

**Files:**
- Create: `mcp-servers/hydrahive-api/tools/sessions.py`
- Create: `mcp-servers/hydrahive-api/tests/test_tools_sessions.py`

- [ ] **Schritt 1: Failing tests**

```python
# tests/test_tools_sessions.py
import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from tools.sessions import list_sessions, get_session, get_messages, send_message

SESSIONS = [{"id": "s1", "agent_id": "buddy", "status": "active"}]
MESSAGES = [{"role": "user", "content": "Hallo"}, {"role": "assistant", "content": "Hi"}]

@pytest.mark.asyncio
async def test_list_sessions(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/sessions").mock(
            return_value=httpx.Response(200, json=SESSIONS)
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await list_sessions(RestClient(auth))
        assert len(result) == 1
        assert result[0]["id"] == "s1"

@pytest.mark.asyncio
async def test_get_session(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/sessions/s1").mock(
            return_value=httpx.Response(200, json={"id": "s1", "total_tokens": 5000})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await get_session(RestClient(auth), "s1")
        assert result["total_tokens"] == 5000

@pytest.mark.asyncio
async def test_get_messages(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/sessions/s1/messages").mock(
            return_value=httpx.Response(200, json=MESSAGES)
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await get_messages(RestClient(auth), "s1", limit=10)
        assert result[1]["content"] == "Hi"

@pytest.mark.asyncio
async def test_send_message(base_url, token):
    with respx.mock:
        respx.post(f"{base_url}/api/sessions/s1/messages").mock(
            return_value=httpx.Response(201, json={"id": "m99", "status": "queued"})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await send_message(RestClient(auth), "s1", "Neue Nachricht")
        assert result["status"] == "queued"
```

- [ ] **Schritt 2: Test ausführen — muss FAIL**

```bash
pytest tests/test_tools_sessions.py -v
```

- [ ] **Schritt 3: `tools/sessions.py` implementieren**

```python
# mcp-servers/hydrahive-api/tools/sessions.py
from __future__ import annotations
from typing import Any
from _rest import RestClient

async def list_sessions(
    client: RestClient, agent_id: str | None = None, limit: int = 20
) -> list[dict]:
    try:
        params: dict = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        result = await client.get("/api/sessions", params=params)
        return result if isinstance(result, list) else result.get("items", [])
    except Exception as e:
        return [{"error": str(e), "code": "sessions_failed"}]

async def get_session(client: RestClient, session_id: str) -> dict[str, Any]:
    try:
        return await client.get(f"/api/sessions/{session_id}")
    except Exception as e:
        return {"error": str(e), "code": "session_not_found"}

async def get_messages(
    client: RestClient, session_id: str, limit: int = 50
) -> list[dict]:
    try:
        result = await client.get(
            f"/api/sessions/{session_id}/messages", params={"limit": limit}
        )
        return result if isinstance(result, list) else result.get("messages", [])
    except Exception as e:
        return [{"error": str(e), "code": "messages_failed"}]

async def send_message(
    client: RestClient, session_id: str, message: str
) -> dict[str, Any]:
    try:
        return await client.post(
            f"/api/sessions/{session_id}/messages",
            body={"content": message, "role": "user"},
        )
    except Exception as e:
        return {"error": str(e), "code": "send_failed"}
```

- [ ] **Schritt 4: Tests grün**

```bash
pytest tests/test_tools_sessions.py -v
```

- [ ] **Schritt 5: Commit**

```bash
git add mcp-servers/hydrahive-api/tools/sessions.py mcp-servers/hydrahive-api/tests/test_tools_sessions.py
git commit -m "feat(mcp): Sessions-Tools — list, get, messages, send"
```

---

## Task 6: Agenten-Tools (`tools/agents.py`)

**Files:**
- Create: `mcp-servers/hydrahive-api/tools/agents.py`
- Create: `mcp-servers/hydrahive-api/tests/test_tools_agents.py`

- [ ] **Schritt 1: Failing tests**

```python
# tests/test_tools_agents.py
import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from tools.agents import list_agents, get_agent, update_agent

AGENTS = [{"id": "buddy", "name": "Buddy", "model": "claude-sonnet-4-6"}]

@pytest.mark.asyncio
async def test_list_agents(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/agents").mock(
            return_value=httpx.Response(200, json=AGENTS)
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await list_agents(RestClient(auth))
        assert result[0]["id"] == "buddy"

@pytest.mark.asyncio
async def test_get_agent(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/agents/buddy").mock(
            return_value=httpx.Response(200, json={"id": "buddy", "max_tokens": 16384})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await get_agent(RestClient(auth), "buddy")
        assert result["max_tokens"] == 16384

@pytest.mark.asyncio
async def test_update_agent(base_url, token):
    with respx.mock:
        respx.patch(f"{base_url}/api/agents/buddy").mock(
            return_value=httpx.Response(200, json={"id": "buddy", "max_tokens": 8192})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await update_agent(RestClient(auth), "buddy", "max_tokens", 8192)
        assert result["max_tokens"] == 8192
```

- [ ] **Schritt 2: Test ausführen — muss FAIL**

```bash
pytest tests/test_tools_agents.py -v
```

- [ ] **Schritt 3: `tools/agents.py` implementieren**

```python
# mcp-servers/hydrahive-api/tools/agents.py
from __future__ import annotations
from typing import Any
from _rest import RestClient

async def list_agents(client: RestClient) -> list[dict]:
    try:
        result = await client.get("/api/agents")
        return result if isinstance(result, list) else result.get("items", [])
    except Exception as e:
        return [{"error": str(e), "code": "agents_failed"}]

async def get_agent(client: RestClient, agent_id: str) -> dict[str, Any]:
    try:
        return await client.get(f"/api/agents/{agent_id}")
    except Exception as e:
        return {"error": str(e), "code": "agent_not_found"}

async def update_agent(
    client: RestClient, agent_id: str, field: str, value: Any
) -> dict[str, Any]:
    try:
        return await client.patch(f"/api/agents/{agent_id}", body={field: value})
    except Exception as e:
        return {"error": str(e), "code": "update_failed"}
```

- [ ] **Schritt 4: Tests grün**

```bash
pytest tests/test_tools_agents.py -v
```

- [ ] **Schritt 5: Commit**

```bash
git add mcp-servers/hydrahive-api/tools/agents.py mcp-servers/hydrahive-api/tests/test_tools_agents.py
git commit -m "feat(mcp): Agenten-Tools — list, get, update"
```

---

## Task 7: Workspace-Tools (`tools/workspace.py`)

**Files:**
- Create: `mcp-servers/hydrahive-api/tools/workspace.py`
- Create: `mcp-servers/hydrahive-api/tests/test_tools_workspace.py`

- [ ] **Schritt 1: Failing tests**

```python
# tests/test_tools_workspace.py
import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from tools.workspace import list_projects, list_files, read_file

PROJECTS = [{"id": "p1", "name": "HydraHive2"}]

@pytest.mark.asyncio
async def test_list_projects(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/projects").mock(
            return_value=httpx.Response(200, json=PROJECTS)
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await list_projects(RestClient(auth))
        assert result[0]["name"] == "HydraHive2"

@pytest.mark.asyncio
async def test_list_files(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/projects/p1/files").mock(
            return_value=httpx.Response(200, json={"entries": [{"name": "README.md", "type": "file"}]})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await list_files(RestClient(auth), "p1")
        assert result["entries"][0]["name"] == "README.md"

@pytest.mark.asyncio
async def test_read_file(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/projects/p1/files/read").mock(
            return_value=httpx.Response(200, json={"content": "# Hello", "path": "README.md"})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await read_file(RestClient(auth), "p1", "README.md")
        assert result["content"] == "# Hello"
```

- [ ] **Schritt 2: Test ausführen — muss FAIL**

```bash
pytest tests/test_tools_workspace.py -v
```

- [ ] **Schritt 3: `tools/workspace.py` implementieren**

```python
# mcp-servers/hydrahive-api/tools/workspace.py
from __future__ import annotations
from typing import Any
from _rest import RestClient

async def list_projects(client: RestClient) -> list[dict]:
    try:
        result = await client.get("/api/projects")
        return result if isinstance(result, list) else result.get("items", [])
    except Exception as e:
        return [{"error": str(e), "code": "projects_failed"}]

async def list_files(
    client: RestClient, project_id: str, path: str = ""
) -> dict[str, Any]:
    try:
        params = {"path": path} if path else {}
        return await client.get(f"/api/projects/{project_id}/files", params=params)
    except Exception as e:
        return {"error": str(e), "code": "files_failed"}

async def read_file(
    client: RestClient, project_id: str, path: str
) -> dict[str, Any]:
    try:
        return await client.get(
            f"/api/projects/{project_id}/files/read", params={"path": path}
        )
    except Exception as e:
        return {"error": str(e), "code": "read_failed"}
```

- [ ] **Schritt 4: Tests grün**

```bash
pytest tests/test_tools_workspace.py -v
```

- [ ] **Schritt 5: Commit**

```bash
git add mcp-servers/hydrahive-api/tools/workspace.py mcp-servers/hydrahive-api/tests/test_tools_workspace.py
git commit -m "feat(mcp): Workspace-Tools — projects, files, read"
```

---

## Task 8: Datamining-Tools (`tools/datamining.py`)

**Files:**
- Create: `mcp-servers/hydrahive-api/tools/datamining.py`
- Create: `mcp-servers/hydrahive-api/tests/test_tools_datamining.py`

- [ ] **Schritt 1: Failing tests**

```python
# tests/test_tools_datamining.py
import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from tools.datamining import dm_search, dm_get_session, dm_list_sessions, dm_stats

@pytest.mark.asyncio
async def test_dm_search(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/datamining/search").mock(
            return_value=httpx.Response(200, json={"results": [{"event": "test"}], "total": 1})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await dm_search(RestClient(auth), q="test")
        assert result["total"] == 1

@pytest.mark.asyncio
async def test_dm_get_session(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/datamining/sessions/s1").mock(
            return_value=httpx.Response(200, json={"session_id": "s1", "events": []})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await dm_get_session(RestClient(auth), "s1")
        assert result["session_id"] == "s1"

@pytest.mark.asyncio
async def test_dm_list_sessions(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/datamining/sessions").mock(
            return_value=httpx.Response(200, json=[{"session_id": "s1", "event_count": 42}])
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await dm_list_sessions(RestClient(auth))
        assert result[0]["event_count"] == 42

@pytest.mark.asyncio
async def test_dm_stats(base_url, token):
    with respx.mock:
        respx.get(f"{base_url}/api/datamining/stats/latest").mock(
            return_value=httpx.Response(200, json={"total_cost_usd": 9.99})
        )
        auth = Auth(base_url=base_url, api_key=token)
        result = await dm_stats(RestClient(auth))
        assert result["total_cost_usd"] == 9.99
```

- [ ] **Schritt 2: Test ausführen — muss FAIL**

```bash
pytest tests/test_tools_datamining.py -v
```

- [ ] **Schritt 3: `tools/datamining.py` implementieren**

```python
# mcp-servers/hydrahive-api/tools/datamining.py
from __future__ import annotations
from typing import Any
from _rest import RestClient

async def dm_search(
    client: RestClient,
    q: str = "",
    event_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    try:
        params: dict = {"q": q, "limit": limit}
        if event_type:
            params["event_type"] = event_type
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        return await client.get("/api/datamining/search", params=params)
    except Exception as e:
        return {"error": str(e), "code": "dm_search_failed"}

async def dm_get_session(client: RestClient, session_id: str) -> dict[str, Any]:
    try:
        return await client.get(f"/api/datamining/sessions/{session_id}")
    except Exception as e:
        return {"error": str(e), "code": "dm_session_failed"}

async def dm_list_sessions(client: RestClient, limit: int = 20) -> list[dict]:
    try:
        result = await client.get("/api/datamining/sessions", params={"limit": limit})
        return result if isinstance(result, list) else result.get("items", [])
    except Exception as e:
        return [{"error": str(e), "code": "dm_list_failed"}]

async def dm_stats(client: RestClient) -> dict[str, Any]:
    try:
        return await client.get("/api/datamining/stats/latest")
    except Exception as e:
        return {"error": str(e), "code": "dm_stats_failed"}
```

- [ ] **Schritt 4: Tests grün**

```bash
pytest tests/test_tools_datamining.py -v
```

- [ ] **Schritt 5: Commit**

```bash
git add mcp-servers/hydrahive-api/tools/datamining.py mcp-servers/hydrahive-api/tests/test_tools_datamining.py
git commit -m "feat(mcp): Datamining-Tools — search, session, list, stats"
```

---

## Task 9: AgentLink-Client (`_agentlink.py`)

**Files:**
- Create: `mcp-servers/hydrahive-api/_agentlink.py`
- Create: `mcp-servers/hydrahive-api/tests/test_agentlink.py`

- [ ] **Schritt 1: Failing tests**

```python
# tests/test_agentlink.py
import asyncio
import pytest
import respx
import httpx
from _auth import Auth
from _rest import RestClient
from _agentlink import AgentLinkClient

@pytest.mark.asyncio
async def test_send_state_post_korrekte_url(base_url, token):
    with respx.mock:
        respx.post(f"{base_url}/agentlink/api/states").mock(
            return_value=httpx.Response(201, json={
                "id": "state-1", "agent_id": "claude-code",
                "task": {"type": "feature", "description": "test", "priority": 5, "status": "in_progress"}
            })
        )
        auth = Auth(base_url=base_url, api_key=token)
        client = RestClient(auth)
        al = AgentLinkClient(rest=client, agent_id="claude-code", base_url=base_url)
        state = await al.send_state(
            to_agent="buddy",
            task_type="feature",
            description="Bitte erledige X",
        )
        assert state["id"] == "state-1"

@pytest.mark.asyncio
async def test_check_inbox_leer_wenn_queue_leer(base_url, token):
    auth = Auth(base_url=base_url, api_key=token)
    client = RestClient(auth)
    al = AgentLinkClient(rest=client, agent_id="claude-code", base_url=base_url)
    result = al.drain_inbox()
    assert result == []

@pytest.mark.asyncio
async def test_eingehende_handoff_landet_in_queue(base_url, token):
    auth = Auth(base_url=base_url, api_key=token)
    client = RestClient(auth)
    al = AgentLinkClient(rest=client, agent_id="claude-code", base_url=base_url)
    # Direkt in Queue schreiben (simuliert WS-Empfang)
    await al._queue.put({"id": "state-99", "task": {"description": "Tue das"}})
    result = al.drain_inbox()
    assert len(result) == 1
    assert result[0]["id"] == "state-99"
```

- [ ] **Schritt 2: Test ausführen — muss FAIL**

```bash
pytest tests/test_agentlink.py -v
```

- [ ] **Schritt 3: `_agentlink.py` implementieren**

```python
# mcp-servers/hydrahive-api/_agentlink.py
from __future__ import annotations
import asyncio
import json
import logging
import os
from typing import Any
import websockets
from _rest import RestClient

logger = logging.getLogger(__name__)

class AgentLinkClient:
    def __init__(self, rest: RestClient, agent_id: str, base_url: str):
        self.rest = rest
        self.agent_id = agent_id
        self.base_url = base_url.rstrip("/")
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._connected = False
        self._last_error: str | None = None
        self._ws_task: asyncio.Task | None = None

    @property
    def al_rest_url(self) -> str:
        return self.base_url + "/agentlink/api"

    @property
    def al_ws_url(self) -> str:
        # https → wss, http → ws
        ws_base = self.base_url.replace("https://", "wss://").replace("http://", "ws://")
        return ws_base + "/agentlink/ws/"

    async def send_state(
        self,
        to_agent: str,
        task_type: str,
        description: str,
        context: dict | None = None,
    ) -> dict[str, Any]:
        body: dict = {
            "agent_id": self.agent_id,
            "task": {
                "type": task_type,
                "description": description,
                "priority": 5,
                "status": "in_progress",
            },
            "handoff": {
                "to_agent": to_agent,
                "reason": description,
                "required_skills": [],
            },
        }
        if context:
            body["context"] = context
        return await self.rest.post(f"/agentlink/api/states", body=body)

    async def reply_to_handoff(self, state_id: str, result: str) -> dict[str, Any]:
        body: dict = {
            "agent_id": self.agent_id,
            "task": {
                "type": "feature",
                "description": result,
                "priority": 5,
                "status": "completed",
            },
            "handoff": {
                "to_agent": "reply",
                "reason": f"reply_to:{state_id}",
                "required_skills": [],
            },
        }
        return await self.rest.post("/agentlink/api/states", body=body)

    def drain_inbox(self) -> list[dict]:
        items = []
        while not self._queue.empty():
            try:
                items.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return items

    def is_connected(self) -> bool:
        return self._connected

    def last_error(self) -> str | None:
        return self._last_error

    async def start(self) -> None:
        self._ws_task = asyncio.create_task(self._listen_loop())

    async def stop(self) -> None:
        if self._ws_task:
            self._ws_task.cancel()

    async def _listen_loop(self) -> None:
        retry_delay = 1.0
        while True:
            try:
                await self.rest.auth.ensure_token()
                headers = self.rest.auth.headers()
                # AgentLink WS erwartet agent_id als Query-Parameter
                ws_url = f"{self.al_ws_url}?agent_id={self.agent_id}"
                async with websockets.connect(
                    ws_url, additional_headers=headers, ssl=None
                ) as ws:
                    self._connected = True
                    self._last_error = None
                    retry_delay = 1.0
                    logger.info("AgentLink WS verbunden: %s", ws_url)
                    async for raw in ws:
                        await self._handle_message(raw)
            except Exception as e:
                self._connected = False
                self._last_error = str(e)
                logger.warning("AgentLink WS Fehler: %s — retry in %ss", e, retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30.0)

    async def _handle_message(self, raw: str) -> None:
        try:
            event = json.loads(raw)
            if event.get("type") == "handoff_received":
                state_id = event.get("state_id")
                if state_id:
                    state = await self.rest.get(f"/agentlink/api/states/{state_id}")
                    await self._queue.put(state)
        except Exception as e:
            logger.debug("WS-Message parse error: %s", e)
```

- [ ] **Schritt 4: Tests grün**

```bash
pytest tests/test_agentlink.py -v
```

- [ ] **Schritt 5: Commit**

```bash
git add mcp-servers/hydrahive-api/_agentlink.py mcp-servers/hydrahive-api/tests/test_agentlink.py
git commit -m "feat(mcp): AgentLink-Client — WebSocket + Queue + send/reply"
```

---

## Task 10: AgentLink-Tools (`tools/agentlink.py`)

**Files:**
- Create: `mcp-servers/hydrahive-api/tools/agentlink.py`

- [ ] **Schritt 1: `tools/agentlink.py` implementieren**
(Kein separater Test — testet direkt gegen `_agentlink.py` das bereits getestet ist)

```python
# mcp-servers/hydrahive-api/tools/agentlink.py
from __future__ import annotations
from typing import Any
from _agentlink import AgentLinkClient
from _rest import RestClient

async def al_status(rest: RestClient, al: AgentLinkClient) -> dict[str, Any]:
    try:
        info = await rest.get("/api/agentlink/status")
        return {
            **info,
            "ws_connected": al.is_connected(),
            "ws_last_error": al.last_error(),
            "inbox_count": al._queue.qsize(),
            "our_agent_id": al.agent_id,
        }
    except Exception as e:
        return {"error": str(e), "code": "al_status_failed"}

async def al_send(
    al: AgentLinkClient,
    to_agent: str,
    task_type: str,
    description: str,
    context: dict | None = None,
) -> dict[str, Any]:
    try:
        return await al.send_state(
            to_agent=to_agent,
            task_type=task_type,
            description=description,
            context=context,
        )
    except Exception as e:
        return {"error": str(e), "code": "al_send_failed"}

def al_check_inbox(al: AgentLinkClient) -> list[dict]:
    return al.drain_inbox()

async def al_reply(
    al: AgentLinkClient, state_id: str, result: str
) -> dict[str, Any]:
    try:
        return await al.reply_to_handoff(state_id=state_id, result=result)
    except Exception as e:
        return {"error": str(e), "code": "al_reply_failed"}
```

- [ ] **Schritt 2: Commit**

```bash
git add mcp-servers/hydrahive-api/tools/agentlink.py
git commit -m "feat(mcp): AgentLink-Tools — status, send, inbox, reply"
```

---

## Task 11: Haupt-Server (`server.py`)

**Files:**
- Create: `mcp-servers/hydrahive-api/server.py`

- [ ] **Schritt 1: `server.py` implementieren**

```python
#!/usr/bin/env python3
# mcp-servers/hydrahive-api/server.py
"""HydraHive API MCP-Server — Claude Code als interner HydraHive-Agent."""
from __future__ import annotations
import asyncio
import os
from mcp.server.fastmcp import FastMCP
from _auth import Auth
from _rest import RestClient
from _agentlink import AgentLinkClient
import tools.system as sys_tools
import tools.sessions as session_tools
import tools.agents as agent_tools
import tools.workspace as ws_tools
import tools.datamining as dm_tools
import tools.agentlink as al_tools

mcp = FastMCP("hydrahive")

_auth = Auth()
_rest = RestClient(_auth)
_al = AgentLinkClient(
    rest=_rest,
    agent_id=os.environ.get("HH_AGENT_ID", "claude-code"),
    base_url=_auth.base_url,
)

# --- System ---
@mcp.tool()
async def hh_status() -> dict:
    """HydraHive Health-Status, Version und Uptime."""
    return await sys_tools.get_status(_rest)

@mcp.tool()
async def hh_token_stats() -> dict:
    """Token-Verbrauch und Kostenübersicht."""
    return await sys_tools.get_token_stats(_rest)

# --- Sessions ---
@mcp.tool()
async def hh_list_sessions(agent_id: str = "", limit: int = 20) -> list:
    """Alle Sessions auflisten. agent_id optional als Filter."""
    return await session_tools.list_sessions(_rest, agent_id=agent_id or None, limit=limit)

@mcp.tool()
async def hh_get_session(session_id: str) -> dict:
    """Details und Token-Verbrauch einer Session."""
    return await session_tools.get_session(_rest, session_id)

@mcp.tool()
async def hh_get_messages(session_id: str, limit: int = 50) -> list:
    """Nachrichten-Verlauf einer Session."""
    return await session_tools.get_messages(_rest, session_id, limit)

@mcp.tool()
async def hh_send_message(session_id: str, message: str) -> dict:
    """Nachricht in eine laufende Session injizieren."""
    return await session_tools.send_message(_rest, session_id, message)

# --- Agenten ---
@mcp.tool()
async def hh_list_agents() -> list:
    """Alle HydraHive-Agenten mit Kurzinfo."""
    return await agent_tools.list_agents(_rest)

@mcp.tool()
async def hh_get_agent(agent_id: str) -> dict:
    """Vollständige Config eines Agenten."""
    return await agent_tools.get_agent(_rest, agent_id)

@mcp.tool()
async def hh_update_agent(agent_id: str, field: str, value: str) -> dict:
    """Ein Config-Feld eines Agenten setzen."""
    return await agent_tools.update_agent(_rest, agent_id, field, value)

# --- Workspace ---
@mcp.tool()
async def hh_list_projects() -> list:
    """Alle HydraHive-Projekte."""
    return await ws_tools.list_projects(_rest)

@mcp.tool()
async def hh_list_files(project_id: str, path: str = "") -> dict:
    """Verzeichnis-Listing eines Projekt-Workspaces."""
    return await ws_tools.list_files(_rest, project_id, path)

@mcp.tool()
async def hh_read_file(project_id: str, path: str) -> dict:
    """Datei aus Projekt-Workspace lesen (read-only)."""
    return await ws_tools.read_file(_rest, project_id, path)

# --- Datamining ---
@mcp.tool()
async def hh_dm_search(
    q: str = "",
    event_type: str = "",
    from_date: str = "",
    to_date: str = "",
    limit: int = 50,
) -> dict:
    """Session-Events durchsuchen."""
    return await dm_tools.dm_search(
        _rest,
        q=q,
        event_type=event_type or None,
        from_date=from_date or None,
        to_date=to_date or None,
        limit=limit,
    )

@mcp.tool()
async def hh_dm_get_session(session_id: str) -> dict:
    """Komplette Session aus Datamining rekonstruieren."""
    return await dm_tools.dm_get_session(_rest, session_id)

@mcp.tool()
async def hh_dm_list_sessions(limit: int = 20) -> list:
    """Letzte Sessions im Datamining-Index."""
    return await dm_tools.dm_list_sessions(_rest, limit)

@mcp.tool()
async def hh_dm_stats() -> dict:
    """Token/Kosten-Statistiken aus Datamining."""
    return await dm_tools.dm_stats(_rest)

# --- AgentLink ---
@mcp.tool()
async def hh_al_status() -> dict:
    """AgentLink-Verbindungsstatus und bekannte Agenten."""
    return await al_tools.al_status(_rest, _al)

@mcp.tool()
async def hh_al_send(
    to_agent: str, task_type: str, description: str
) -> dict:
    """Handoff/State an einen anderen HydraHive-Agenten schicken."""
    return await al_tools.al_send(_al, to_agent, task_type, description)

@mcp.tool()
async def hh_al_check_inbox() -> list:
    """Eingegangene Handoffs aus der AgentLink-Queue lesen."""
    return al_tools.al_check_inbox(_al)

@mcp.tool()
async def hh_al_reply(state_id: str, result: str) -> dict:
    """Auf einen eingegangenen Handoff antworten."""
    return await al_tools.al_reply(_al, state_id, result)


async def _startup() -> None:
    await _auth.ensure_token()
    await _al.start()

async def _shutdown() -> None:
    await _al.stop()

if __name__ == "__main__":
    asyncio.run(_startup())
    try:
        mcp.run()
    finally:
        asyncio.run(_shutdown())
```

- [ ] **Schritt 2: Syntax-Check**

```bash
cd mcp-servers/hydrahive-api && python -c "import server; print('OK')"
```

Erwartet: `OK` (oder Fehler wenn HH_BASE_URL fehlt — das ist ok, nur Syntax prüfen)

- [ ] **Schritt 3: Alle Tests grün**

```bash
pytest tests/ -v
```

Erwartet: Alle Tests PASSED

- [ ] **Schritt 4: Commit**

```bash
git add mcp-servers/hydrahive-api/server.py
git commit -m "feat(mcp): Haupt-Server — alle Tools registriert + Startup/Shutdown"
```

---

## Task 12: Claude Code Integration

**Files:**
- Modify: `~/.claude/settings.json` (global) **oder** `.claude/settings.json` (projektlokal)

- [ ] **Schritt 1: MCP-Eintrag in Claude Code Settings hinzufügen**

Globale Settings öffnen (`~/.claude/settings.json`) und `mcpServers` ergänzen:

```json
{
  "mcpServers": {
    "hydrahive": {
      "command": "python",
      "args": ["/home/till/claudeneu/mcp-servers/hydrahive-api/server.py"],
      "env": {
        "HH_BASE_URL": "https://192.168.3.22",
        "HH_USER": "admin",
        "HH_PASS": "HIER_PASSWORT_EINTRAGEN",
        "HH_AGENT_ID": "claude-code",
        "HH_VERIFY_SSL": "0"
      }
    }
  }
}
```

- [ ] **Schritt 2: README anlegen**

```markdown
# HydraHive API MCP-Server

MCP-Server der Claude Code als internen HydraHive-Agenten einbindet.

## Setup

    cd mcp-servers/hydrahive-api
    pip install -e ".[dev]"

## Tests

    pytest tests/ -v

## Konfiguration (Env-Variablen)

| Variable | Pflicht | Beschreibung |
|---|---|---|
| HH_BASE_URL | ✅ | https://192.168.3.22 |
| HH_USER | ✅* | Admin-Username |
| HH_PASS | ✅* | Admin-Passwort |
| HH_API_KEY | ✅* | Alternativ zu User/Pass (hhk_...) |
| HH_AGENT_ID | — | Name in AgentLink (default: claude-code) |
| HH_VERIFY_SSL | — | 1 = SSL prüfen (default: 0) |

*Entweder HH_USER+HH_PASS ODER HH_API_KEY
```

- [ ] **Schritt 3: Claude Code neu starten und testen**

```
/reload-plugins
```

Dann testen:
```
hh_status()           → sollte Health-JSON zurückgeben
hh_list_agents()      → sollte Agenten-Liste zeigen
hh_al_status()        → sollte AgentLink-Status zeigen
```

- [ ] **Schritt 4: Final-Commit**

```bash
git add mcp-servers/hydrahive-api/README.md
git commit -m "docs(mcp): README für hydrahive-api MCP-Server"
git push origin main
```
