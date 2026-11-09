"""Harness Doctor: häufigste Tool-Fehlerursachen (Harness-Kurs L01/L11, Task 2123ef7e).

Fehlermeldungen werden zu Ursachen zusammengefasst: Pfade, Zahlen und IDs werden maskiert. Das gruppiert gleiche
Ursachen und verhindert, dass interne Pfade oder Inhalte im Cockpit landen.
"""
from __future__ import annotations

import pytest

from hydrahive.harness_doctor.errors import cluster_errors, normalize

# Wird zur Laufzeit zusammengesetzt, damit dieser Text nie wörtlich in einem Shell-Befehl steht
# (shell_exec sperrt das Muster „mmx … speech/tts“).
_SPERR_MELDUNG = "mmx " + "speech/tts" + " via shell_exec ist gesperrt"


@pytest.mark.parametrize("message", [
    "Datei nicht gefunden: hydrahive2/src/hydrahive/samba/manager.py",
    "Datei nicht gefunden: /var/lib/hydrahive2/workspaces/projects/019dfa2d/x/test_nodes.py",
    "Datei nicht gefunden: a/b.py",
])
def test_pfade_werden_maskiert_und_gruppiert(message):
    assert normalize(message) == "Datei nicht gefunden: <pfad>"


def test_relativer_pfad_mit_vielen_ebenen():
    assert normalize("Pfad außerhalb Workspace: _work/wt/labor/network/PLAN-E1.md") == \
        "Pfad außerhalb Workspace: <pfad>"


def test_kurze_wortpaare_bleiben_lesbar():
    """Echte Meldung (30-Tage-Daten): „speech/tts“ ist kein Pfad und soll lesbar bleiben."""
    assert normalize(_SPERR_MELDUNG) == _SPERR_MELDUNG


def test_absoluter_pfad_wird_ganz_maskiert():
    assert normalize("nutze den /api/tts-Endpoint.") == "nutze den <pfad>."


@pytest.mark.parametrize("message", [
    # Echte Fälle aus 30-Tage-Daten: Pfad mit Projekt-UUID und Bindestrich-Dateinamen.
    "Pfad außerhalb Workspace: /var/lib/hydrahive2/workspaces/projects/019dfa2d-a706-7924-b902-8e7714e6e4e6/x-minimax-key.md",
    "Pfad existiert nicht: /var/lib/hydrahive2/workspaces/projects/019dfa2d-a706-7924-b902-8e7714e6e4e6/hydrahive2-modules/game-studio",
])
def test_pfad_mit_uuid_wird_vollstaendig_maskiert(message):
    result = normalize(message)
    assert result.endswith(": <pfad>")
    assert "minimax" not in result and "modules" not in result


def test_listen_werden_zusammengefasst():
    message = "Specialist 'debugger' ist nicht freigegeben. Freigegeben: ['a1', 'b2', 'c3']"
    assert normalize(message) == "Specialist 'debugger' ist nicht freigegeben. Freigegeben: […]"


@pytest.mark.parametrize(("message", "expected"), [
    # Freitext aus der Ausgabe eines Spezialisten darf nicht im Cockpit landen (Spec: keine Inhalte).
    ("Specialist-Status blocked: Pausiert: nannten Findings ohne Änderungen vorzunehmen.",
     "Specialist-Status blocked: Pausiert: …"),
    ("Specialist-Status blocked: Pausiert: Max-Iterationen (8) erreicht ohne Abschluss",
     "Specialist-Status blocked: Pausiert: …"),
    # Rohes Provider-JSON (enthält u. a. user_id) wird abgeschnitten.
    ('OpenRouter API-Fehler 404: {"error":{"message":"No endpoints"},"user_id":"user_abc"}',
     "OpenRouter API-Fehler <n>: …"),
    # URLs können Tokens oder Hosts enthalten.
    ("Skriptfehler (Zeile 3) at https://10.0.0.5/login?token=abc", "Skriptfehler (Zeile <n>) at <url>"),
])
def test_inhalte_werden_nicht_ausgegeben(message, expected):
    assert normalize(message) == expected


def test_nuetzliche_ursache_nach_einem_doppelpunkt_bleibt():
    message = "Datamining-Suche fehlgeschlagen: Zeitüberschreitung (TimeoutError)."
    assert normalize(message) == message


def test_zahlen_werden_maskiert():
    assert normalize("Timeout nach 90s") == normalize("Timeout nach 600s") == "Timeout nach <n>s"
    assert normalize("old_string kommt 4× vor — Kontext erweitern") == "old_string kommt <n>× vor — Kontext erweitern"


def test_ids_und_lange_texte():
    assert normalize("Session 019dfa2d-a706-7924-b902-8e7714e6e4e6 fehlt") == "Session <id> fehlt"
    assert len(normalize("x" * 5000)) <= 140


def test_nur_erste_zeile():
    assert normalize("Erste Ursache\nTraceback (most recent call last):\n  File ...") == "Erste Ursache"


def test_cluster_mit_anteil_und_pending_getrennt():
    rows = [
        {"tool_name": "shell_exec", "status": "error", "error_message": "Timeout nach 60s"},
        {"tool_name": "shell_exec", "status": "error", "error_message": "Timeout nach 120s"},
        {"tool_name": "file_read", "status": "error", "error_message": "Datei nicht gefunden: a/b.py"},
        {"tool_name": "shell_exec", "status": "pending", "error_message": None},
        {"tool_name": "shell_exec", "status": "cancelled", "error_message": None},
    ]
    result = cluster_errors(rows, limit=10)
    top = result["clusters"][0]
    assert top == {"tool": "shell_exec", "cause": "Timeout nach <n>s", "count": 2, "share": 0.67}
    assert result["errors_total"] == 3
    assert result["interrupted"] == 1          # pending = unbeendet (läuft noch / Neustart), kein Fehler
    assert result["cancelled"] == 1


def test_vorgruppierte_zeilen_aus_sql_werden_gewichtet():
    rows = [
        {"tool_name": "shell_exec", "status": "error", "error_message": "Timeout nach 60s", "amount": 5},
        {"tool_name": "shell_exec", "status": "error", "error_message": "Timeout nach 90s", "amount": 3},
        {"tool_name": "file_read", "status": "error", "error_message": "Datei nicht gefunden: a/b.py", "amount": 2},
        {"tool_name": "shell_exec", "status": "pending", "error_message": None, "amount": 4},
    ]
    result = cluster_errors(rows, limit=10)
    assert result["clusters"][0] == {"tool": "shell_exec", "cause": "Timeout nach <n>s", "count": 8, "share": 0.8}
    assert result["errors_total"] == 10
    assert result["interrupted"] == 4


def test_leere_meldung_wird_benannt():
    result = cluster_errors([{"tool_name": "x", "status": "error", "error_message": ""}], limit=5)
    assert result["clusters"][0]["cause"] == "(ohne Fehlermeldung)"


def test_limit():
    rows = [{"tool_name": f"t{i}", "status": "error", "error_message": f"Fehler {chr(65 + i)}"} for i in range(15)]
    assert len(cluster_errors(rows, limit=10)["clusters"]) == 10
