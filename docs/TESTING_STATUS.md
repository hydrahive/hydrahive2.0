# Testing Status — HydraHive2

> **Last Updated:** 2026-05-09
> **Status:** 🟡 Foundation steht, weite Lücken in der Coverage

---

## Quick Stats

```
┌─────────────────────────────────────────────────────────┐
│  Test-Dateien:        6                                 │
│  Tests gesamt:        60                                │
│  Pass:                60 (100%)                         │
│  Laufzeit:            ~4.5s                             │
│  CI:                  ✅ läuft (.github/workflows/      │
│                          pytest.yml), letzte 10 grün    │
│  Module getestet:     6 von ~28 (~21%)                  │
└─────────────────────────────────────────────────────────┘
```

Lokal laufen: `pip install -e core/ && pytest core/tests/ -v`
CI: jeder Push auf `main` und jede PR.

---

## Was getestet ist

| Datei | Tests | Bereich |
|---|---|---|
| `test_auth.py` | 10 | JWT-Encode/Decode, `require_auth`, `require_admin`, optional auth |
| `test_session_ownership.py` | 6 | User darf eigene, Admin darf fremde, Fremde 403 |
| `test_lockout.py` | 8 | Login-Lockout per User + per IP, Threshold/Reset/Expiry |
| `test_api_integration.py` | 8 | Login, /me, Sessions-CRUD via TestClient |
| `test_runner_cache.py` | 12 | Anthropic Prompt-Cache (1h-TTL, letztes Tool, Stable/Volatile-Split) |
| `test_reasoning_effort.py` | 14 | Thinking-Block-Generierung pro Effort-Level |

---

## Was NICHT getestet ist (Risiko-Tabelle)

| Modul | Risiko | Grund |
|---|---|---|
| **Runner Tool-Loop** | 🔴 | Kern-Loop, Tool-Execution, Iteration-Logik |
| **Compaction** | 🔴 | Append-only mit `firstKeptEntryId`, Datenverlust-Risiko |
| **Memory v2** (Compress/Crystallize/Inject) | 🔴 | LLM-Pipeline, drei-stufig, neuestes System |
| **shell_exec** | 🟡 | Path-Traversal, Quoting (Security) |
| **file_patch** | 🟡 | Diff-Anwendung |
| **MCP-Client** (stdio/HTTP/SSE) | 🟡 | Externe Prozesse |
| **AgentLink-Bridge** | 🟡 | Inter-Agent-Kommunikation |
| **DB-Migrationen** | 🟡 | Schema-Drift bei Update |
| **Datamining-Mirror** (Postgres) | 🟢 | Optional, durch pgvector-Health-Check abgesichert |

---

## CI-Pipeline

`.github/workflows/pytest.yml`:
- Trigger: push auf main, jeder PR
- Setup: Python 3.12, `pip install -e core/`
- Run: `cd core && PYTHONPATH=src pytest tests/ -v --tb=short`
- Laufzeit: ~40-50s, alle 10 letzten Runs grün

---

## Bekannte Warnings

- `audioop is deprecated` — discord.py Transitive (Python 3.13-Vorschau, nicht kritisch)
- `InsecureKeyLengthWarning: HMAC key 15/30/31 bytes` — Test-Fixtures nutzen kurze Keys; Produktion nutzt `HH_SECRET_KEY` aus Settings (länger)

---

## Roadmap (vorgeschlagen, nicht beschlossen)

Das ist Phase 2 aus dem Cleanup-Plan. Vorschlag:
1. **Runner-Tests** (Mock LLM-Bridge, Tool-Use-Block-Schleife) — höchster ROI
2. **Compaction-Tests** (firstKeptEntryId, Sliding-Window-Boundaries)
3. **Memory v2** (Compress/Crystallize Smoke-Tests, Persistenz)
4. **shell_exec** (Path-Traversal, Workspace-Boundary)
