"""Harness-Doctor-Telemetrie mit echter Test-DB (Task 2123ef7e).

Fehlerrate zählt nur echte Fehler (status='error'). `pending` (unbeendet: läuft noch oder Neustart) und `cancelled`
(vom Nutzer gestoppt) werden getrennt ausgewiesen. Ursachen kommen maskiert an, Pfade verlassen den Doctor nicht.
"""
from __future__ import annotations

import json


def _seed_tools(entries: list[tuple[str, str, str | None]]) -> None:
    from hydrahive.db import messages as messages_db
    from hydrahive.db import sessions as sessions_db
    from hydrahive.db import tools as tools_db

    session = sessions_db.create(agent_id="agent-x", user_id="tester", title="doctor")
    message = messages_db.append(session.id, "assistant", "x")
    for tool, status, error in entries:
        call = tools_db.create(message.id, tool, {}, session_id=session.id)
        if status != "pending":
            tools_db.finish(call.id, "", status=status, error_message=error)


def test_fehlerrate_zaehlt_nur_echte_fehler(mod_env):
    from hydrahive.harness_doctor.collector import _telemetry

    _seed_tools([
        ("shell_exec", "success", None),
        ("shell_exec", "error", "Timeout nach 60s"),
        ("shell_exec", "pending", None),
        ("shell_exec", "cancelled", None),
    ])
    telemetry = _telemetry(24)
    assert telemetry["tool_calls"] == 4
    assert telemetry["tool_errors"] == 1
    assert telemetry["tool_interrupted"] == 1
    assert telemetry["tool_cancelled"] == 1


def test_ursachen_maskiert_und_ohne_pfade(mod_env):
    from hydrahive.harness_doctor.collector import _telemetry

    _seed_tools([
        ("file_read", "error", "Datei nicht gefunden: /home/geheim/projekt/secret.py"),
        ("file_read", "error", "Datei nicht gefunden: src/a/b.py"),
        ("file_read", "error", "Datei nicht gefunden: src/a/b.py"),   # identisch → in SQL gruppiert
    ])
    causes = _telemetry(24)["error_causes"]
    assert causes["errors_total"] == 3
    assert causes["clusters"] == [
        {"tool": "file_read", "cause": "Datei nicht gefunden: <pfad>", "count": 3, "share": 1.0},
    ]
    assert "geheim" not in json.dumps(causes)


def test_ursachen_im_doctor_ergebnis_nicht_im_snapshot(mod_env):
    from hydrahive.harness_doctor.collector import run_doctor

    _seed_tools([("shell_exec", "error", "Timeout nach 60s")])
    result = run_doctor(24)
    assert result["error_causes"]["clusters"][0]["cause"] == "Timeout nach <n>s"
    assert "error_causes" not in result["snapshot"]
    assert result["snapshot"]["tool_errors"] == 1
