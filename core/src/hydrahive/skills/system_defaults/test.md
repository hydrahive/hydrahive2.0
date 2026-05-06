---
name: test
description: Generiert Unit-Tests, Integrations-Tests und Test-Daten. Für das Schreiben von Tests, Verbesserung der Test-Coverage oder Erstellung von Edge-Case-Szenarien.
when_to_use: Wenn Tests für neuen Code geschrieben werden sollen, Coverage verbessert werden soll, oder Edge Cases und Fixtures gebraucht werden.
tools_required: [read_file, write_file, bash, grep]
---

# Test-Generierungs-Skill

## 1. Unit Tests — Python (pytest)

```python
import pytest
from mymodule import my_function

class TestMyFunction:
    def test_normal_case(self):
        assert my_function("input") == "expected"

    def test_empty_input(self):
        assert my_function("") == ""

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            my_function(None)

    @pytest.mark.parametrize("input,expected", [
        ("a", "A"),
        ("hello", "HELLO"),
    ])
    def test_parametrized(self, input, expected):
        assert my_function(input) == expected
```

## 2. FastAPI Integrations-Tests

```python
import pytest
from fastapi.testclient import TestClient
from myapp.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_create_resource(client):
    r = client.post("/api/resource", json={"name": "test"})
    assert r.status_code == 201
    assert r.json()["name"] == "test"

def test_not_found(client):
    r = client.get("/api/resource/99999")
    assert r.status_code == 404
```

## 3. SQLite-Fixtures (HH2-Style)

```python
import pytest
import sqlite3

@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(open("migrations/001_init.sql").read())
    yield conn
    conn.close()

def test_insert_and_query(db):
    db.execute("INSERT INTO sessions (id, agent_id) VALUES (?, ?)", ("s1", "a1"))
    row = db.execute("SELECT * FROM sessions WHERE id = ?", ("s1",)).fetchone()
    assert row["agent_id"] == "a1"
```

## 4. Mocking

```python
from unittest.mock import Mock, patch

def test_with_mock():
    mock_dep = Mock()
    mock_dep.get_data.return_value = {"status": "ok"}
    result = function_using_dep(mock_dep)
    mock_dep.get_data.assert_called_once()

def test_with_patch():
    with patch('mymodule.external_call') as mock:
        mock.return_value = {"data": "mocked"}
        result = function_calling_external()
        assert result["data"] == "mocked"
```

## 5. Coverage prüfen

```bash
pytest --cov=hydrahive --cov-report=html tests/
open htmlcov/index.html
```

## 6. Test-Kategorien

Für jede Funktion Tests schreiben für:
- **Happy Path** — normaler erwarteter Input
- **Edge Cases** — leer, null, Maxlänge
- **Error Cases** — ungültige Typen, fehlende Pflichtfelder
- **Boundary Conditions** — Off-by-one, Limits
- **Auth** — nicht authentifiziert, falsche Permissions
- **Async** — mehrere parallele Aufrufe

## 7. Was einen guten Test ausmacht

- Eine Assertion pro Test (oder eng verwandte)
- Testname beschreibt das Szenario: `test_create_session_returns_201`
- Keine Logik in Tests — deterministischer Input, deterministisches Assert
- Isoliert — kein Shared State zwischen Tests
- Schnell — I/O mocken, In-Memory-DB nutzen
