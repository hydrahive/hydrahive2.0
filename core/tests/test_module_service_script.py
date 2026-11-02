"""Extension-Skripte: begrenzte, geschwärzte Ausgabe für den Modul-SSE-Stream."""
from __future__ import annotations

from pathlib import Path

import pytest


def _script(mod_env: Path, body: str, module_id: str = "demo") -> None:
    path = mod_env / "modules" / module_id / "extension" / "install.sh"
    path.parent.mkdir(parents=True)
    path.write_text("#!/usr/bin/env bash\nset -eu\n" + body, encoding="utf-8")


def test_service_script_liefert_stdout_und_stderr_in_reihenfolge(mod_env):
    from hydrahive.modules import installer

    _script(mod_env, "echo erste\necho zweite >&2\necho dritte\n")

    assert list(installer._run_service_script("demo", "install.sh")) == [
        "erste", "zweite", "dritte",
    ]


def test_service_script_fehler_enthaelt_bereinigten_konkreten_tail(mod_env):
    from hydrahive.modules import installer

    secret = "sk-or-v1-ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    _script(mod_env, f"echo '{secret}'\necho 'xz: Cannot exec: No such file' >&2\nexit 7\n")
    output: list[str] = []

    with pytest.raises(installer.ServiceScriptError) as caught:
        output.extend(installer._run_service_script("demo", "install.sh"))

    assert output[0] == "[REDACTED]"
    assert output[-1] == "xz: Cannot exec: No such file"
    message = str(caught.value)
    assert "exit 7" in message
    assert "xz: Cannot exec: No such file" in message
    assert secret not in message
    assert "/var/lib/" not in message


def test_service_script_begrenzt_zeilenlaenge_und_gesamtmenge(mod_env, monkeypatch):
    from hydrahive.modules import installer, service_script

    monkeypatch.setattr(service_script, "_MAX_LINES", 2)
    monkeypatch.setattr(service_script, "_MAX_LINE_CHARS", 12)
    _script(mod_env, "printf '12345678901234567890\\n'\necho zwei\necho drei\necho vier\n")

    output = list(installer._run_service_script("demo", "install.sh"))

    assert output[0] == "123456789012…"
    assert output[1] == "zwei"
    assert output[2] == "[modules] Script-Ausgabe gekürzt"
    assert len(output) == 3


def test_service_script_begrenzt_auch_den_gesamten_fehler_tail(mod_env, monkeypatch):
    from hydrahive.modules import installer, service_script

    monkeypatch.setattr(service_script, "_ERROR_MAX_CHARS", 80)
    _script(mod_env, "printf '%0200d\\n' 0\necho 'konkrete Ursache' >&2\nexit 9\n")

    with pytest.raises(installer.ServiceScriptError) as caught:
        list(installer._run_service_script("demo", "install.sh"))

    message = str(caught.value)
    assert len(message) < 180
    assert message.endswith("konkrete Ursache")


def test_service_script_zerlegt_carriage_return_fortschritt(mod_env):
    from hydrahive.modules import installer

    _script(mod_env, "printf '10%%\\r20%%\\r100%%\\n'\n")

    assert list(installer._run_service_script("demo", "install.sh")) == ["10%", "20%", "100%"]
