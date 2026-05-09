# Testing Status — HydraHive2

> **Last Updated:** 2026-05-09
> **Status:** 🟢 Foundation steht, Kern-Subsysteme abgedeckt

---

## Quick Stats

```
┌─────────────────────────────────────────────────────────┐
│  Test-Dateien:        17                                │
│  Tests gesamt:        243                               │
│  Pass:                243 (100%)                        │
│  Laufzeit:            ~5s                               │
│  CI:                  ✅ Backend-pytest + ruff + Frontend-tsc │
│                          (.github/workflows/pytest.yml) │
│  Backend-Files:       343 (.py)                         │
│  Frontend-Files:      262 (.ts/.tsx)                    │
└─────────────────────────────────────────────────────────┘
```

Lokal:
```bash
cd core
/home/till/claudeneu/.venv/bin/python -m pytest          # alle 243 Tests
/home/till/claudeneu/.venv/bin/python -m ruff check src tests
```

CI auf jeden Push und jede PR: 2 Jobs (Backend mit ruff+pytest, Frontend mit tsc).

---

## Was getestet ist

| Datei | Tests | Bereich |
|---|---|---|
| `test_memory_store.py` | 32 | Memory v2 Pure Functions: migrate, expiry, Jaccard, contradictions |
| `test_file_tools.py` | 29 | safe_path, file_read/write/patch, Path-Traversal |
| `test_compaction.py` | 28 | Token-Estimation, cut_point, should_compact |
| `test_runner_context.py` | 24 | context.py + dispatcher.py pure Functions |
| `test_shell_exec.py` | 16 | Reject-Pfade, Env-Filter, Cmd-Rewrite, Timeout |
| `test_reasoning_effort.py` | 13 | Thinking-Block-Generierung pro Effort-Level |
| `test_runner_cache.py` | 12 | Anthropic Prompt-Cache (1h-TTL, Stable/Volatile-Split) |
| `test_memory_context_injection.py` | 12 | Crystal-Scope (#113), Threshold-Overrides (#115), Memory-Block-Build |
| `test_crystallize_storage.py` | 11 | Append-only Versioning, get_crystal liefert neuestes (#114) |
| `test_api_integration.py` | 11 | Login, /me, Sessions-CRUD via TestClient |
| `test_auth.py` | 10 | JWT Encode/Decode, require_auth/admin, optional |
| `test_memory_bulk.py` | 9 | write_keys_bulk = 1 read+write für N entries (#116) |
| `test_token_usage.py` | 8 | usage_dict (Anthropic) + usage_from_litellm (OpenAI) |
| `test_observations.py` | 8 | mark_compressed_bulk (#B1 Phase D), edge cases |
| `test_lockout.py` | 8 | Login-Lockout per User + per IP, Threshold/Reset/Expiry |
| `test_session_ownership.py` | 6 | User darf eigene, Admin darf fremde, Fremde 403 |
| `test_llm_config_rmw.py` | 6 | OAuth-Refresh atomic + flock + concurrent multiprocessing |

---

## Subsystem-Coverage-Matrix

| Subsystem | Coverage | Test-Dateien |
|---|---|---|
| **Auth + Sessions** | 🟢 voll | test_auth, test_lockout, test_session_ownership, test_api_integration |
| **Tools** (file/shell) | 🟢 voll | test_file_tools, test_shell_exec |
| **Memory v2 Pipeline** | 🟢 voll | test_memory_store, test_observations, test_memory_bulk, test_crystallize_storage, test_memory_context_injection |
| **Runner / LLM-Bridge** | 🟢 voll | test_runner_context, test_runner_cache, test_reasoning_effort, test_token_usage |
| **Compaction** | 🟢 voll | test_compaction |
| **OAuth-Refresh** | 🟢 voll | test_llm_config_rmw |
| **MCP-Client** | 🟡 ungetestet | — externe Prozesse, Mock-Aufwand hoch |
| **AgentLink-Bridge** | 🟡 ungetestet | — Inter-Agent-Kommunikation |
| **Datamining-Mirror** | 🟢 indirekt | pgvector-Health-Check im Installer |
| **DB-Migrationen** | 🟡 ungetestet | manuelle Verifikation beim Update |

---

## CI-Pipeline

`.github/workflows/pytest.yml` hat zwei Jobs:

**Backend (`backend`):**
- Trigger: push auf main + jede PR
- Setup: Python 3.12, `pip install -e core/`
- Steps: `ruff check src tests` → `pytest tests/ -v --tb=short`
- Laufzeit: ~30s

**Frontend (`frontend`):**
- Setup: Node 20, `npm ci`
- Steps: `npx tsc --noEmit`
- Laufzeit: ~30s

Letzte 10 Runs: alle grün.

---

## Bekannte Warnings (nicht kritisch)

- `audioop is deprecated` — discord.py transitive (Python 3.13-Vorschau)
- `InsecureKeyLengthWarning: HMAC key 15/30/31 bytes` — Test-Fixtures nutzen
  kurze Keys; Produktion nutzt `HH_SECRET_KEY` aus Settings (länger)

---

## Offene Coverage-Lücken

Stand nach Phase-D + Phase-E (siehe HANDOVER.md):

1. **MCP-Client Integration-Tests** — bräuchte einen Mock-MCP-Server. Hoher
   Aufwand, niedriger Nutzen für jetzt.
2. **AgentLink-Bridge** — externer Service, primär smoke via dev-test.
3. **End-to-End** — kein E2E-Test (Browser → Frontend → API → LLM-Mock).
   Für Frontend-Refactor-Sicherheit sinnvoll, aber Betriebsaufwand.

Die historischen Analysen vor dem Test-Push:
- `TEST_DEEP_DIVE.md` (2026-05-06, "0 Unit-Tests")
- `TEST_CHECKLIST.md` (Tracking-Doku während Test-Aufbau)

beide nicht mehr live; Stand-Wahrheit ist diese Datei.
