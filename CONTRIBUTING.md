# Contributing to HydraHive2

> Vor dem ersten Commit: `CLAUDE.md` lesen — die enthält die verbindlichen
> Arbeitsregeln (Datei-Größe, Co-location, Permissions, was-nicht-zu-tun).

---

## Git-Workflow

```bash
# Vor jedem Push: erst pullen
git pull --rebase

# Staged files einzeln — nie git add -A
git add core/src/hydrahive/some_file.py

# Commit
git commit -m "fix(auth): kurze Beschreibung was und warum"

# Push
git push
```

Git-Befehle immer im Repo-Root (`/home/<user>/hydrahive2/` bzw. wo `.git/` liegt).

### Commit-Message-Konventionen

Format: `<type>(<scope>): <kurze Beschreibung>`

**Types:** `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `ci`, `chore`, `style`

**Beispiele:**
```
fix(memory): Re-Crystallize per force=True + append-only Versioning (#114)
feat(auth): Login-Lockout per IP zusätzlich zu per User
refactor(runner): runner.py 271 → 212 + 3 Sub-Module
test(memory): 32 Tests für Memory v2 Store-Logic
```

Issues schließen via Trailer: `Closes #123`. SPEC.md / CLAUDE.md werden in
**standalone-Commits** gepflegt — Pre-Commit-Hook (`installer/git-hooks/pre-commit`)
erzwingt das.

---

## Tests

```bash
cd core
/home/<user>/hydrahive2/.venv/bin/python -m pytest          # alle 243 Tests, ~5s
/home/<user>/hydrahive2/.venv/bin/python -m ruff check src tests
```

Pytest, Ruff, mypy-Linting sind in `core/pyproject.toml` als Dev-Dependencies.

**Frontend:**
```bash
cd frontend
npx tsc --noEmit                                          # TypeScript-Check
```

CI läuft beides auf jeden Push (`.github/workflows/pytest.yml`).

### Test-Konventionen

- Pure Functions — Mock File-IO via `monkeypatch` (siehe `test_memory_bulk.py`,
  `test_observations.py` als Referenz)
- Test-Names beschreiben Verhalten + Erwartung in Deutsch:
  `test_bulk_leere_mappings_returns_0`
- Race-Conditions über `multiprocessing.Process` testen (siehe
  `test_llm_config_rmw.py::test_concurrent_writes_kein_datenverlust`)
- Async via `pytest-asyncio` (im Test-Setup als `asyncio: mode=Mode.STRICT`)

Detail siehe `docs/TESTING_STATUS.md`.

---

## FastAPI-Fehlerformat

Alle API-Fehler haben diese Struktur:

```json
{"detail": {"code": "error_code_string", "params": {}}}
```

In Tests:
```python
assert response.json()["detail"]["code"] == "invalid_credentials"
```

Hilfsfunktionen in `core/tests/conftest.py`: `error_code(response)`,
`bearer(token)`.

---

## Code-Konventionen

### Datei-Größen

**Max ~200 Zeilen pro Datei** — Hard-Limit ~250. Eine Datei = eine
Verantwortung. Wenn drüber: aufteilen, nicht weiterschreiben. Pattern für
Splits siehe Phase-A-Commits (`refactor(...): X → 3 Files`).

### Imports & Lazy-Loads

Top-Level-Imports bevorzugen. Lazy-Import nur bei echten Zyklen oder bei
optionalen Dependencies (z.B. `litellm`, `numpy`).

### Logging statt print

Kein `print()` im Produktions-Code. Modul-Logger:
```python
import logging
logger = logging.getLogger(__name__)
```

### Atomic Writes

JSON-Files via Temp + Rename:
```python
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(data, indent=2))
tmp.replace(path)
```

Concurrent Writers brauchen zusätzlich `fcntl.flock` —
siehe `oauth/_llm_config_rmw.py` als Referenz.

---

## Dateien lesen — gezielt, nicht vollständig

Große Dateien (settings.py, pyproject.toml) enthalten oft hunderte
irrelevante Zeilen. Nutze `grep` oder `file_read` mit dem `grep`-Parameter:

```
file_read(path="settings.py", grep="secret_key|jwt_algorithm")
```

Das gibt nur die relevanten Zeilen zurück — spart Token und Zeit.

---

## Doku-Pflege

- `HANDOVER.md` — fortlaufender Session-State, am Ende jeder größeren Session updaten
- `TESTING_STATUS.md` — bei neuen/entfernten Test-Dateien aktualisieren
- `STRUCTURE.md` — bei neuen Modulen/Verzeichnissen
- `SPEC.md`, `CLAUDE.md` — **nur mit ausdrücklicher Zustimmung von Till**,
  standalone-Commit (siehe CLAUDE.md Regel 8)

Architektur-Dokus für Subsysteme liegen in `docs/architecture/`.
