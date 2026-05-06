# Contributing to HydraHive2

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

Git-Befehle immer im Repo-Root (`/home/till/claudeneu/` oder wo `.git/` liegt).

## Tests

```bash
cd core
PYTHONPATH=src pytest tests/ -v --tb=short
```

pytest ist in `core/pyproject.toml` als Dependency — nach `pip install -e core/` verfügbar.

## FastAPI-Fehlerformat

Alle API-Fehler haben diese Struktur:

```json
{"detail": {"code": "error_code_string", "params": {}}}
```

In Tests: `response.json()["detail"]["code"] == "invalid_credentials"`.
Hilfsfunktionen in `core/tests/conftest.py`: `error_code(response)`, `bearer(token)`.

## Dateien lesen — gezielt, nicht vollständig

Große Dateien (settings.py, pyproject.toml) enthalten oft hunderte irrelevante Zeilen.
Nutze `grep` oder `file_read` mit dem `grep`-Parameter:

```
file_read(path="settings.py", grep="secret_key|jwt_algorithm")
```

Das gibt nur die relevanten Zeilen zurück — spart Token und Zeit.

## Datei-Größen

Max ~200 Zeilen pro Datei. Eine Datei = eine Verantwortung.
