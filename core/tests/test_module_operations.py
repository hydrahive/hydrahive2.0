"""Modul-Abläufe laufen zu Ende, auch wenn niemand mehr zuhört (docs/specs/modul-update-unabhaengig-vom-browser.md)."""
from __future__ import annotations

import threading

import pytest

from hydrahive.modules import operations


@pytest.fixture(autouse=True)
def _free_lock():
    """Jeder Test beginnt ohne laufenden Ablauf und hinterlässt keinen."""
    yield
    op = operations.current()
    if op is not None:
        op.wait(5)


def _gen(steps: list[str], reached: list[str], gate: threading.Event | None = None, fail: bool = False):
    for i, s in enumerate(steps):
        if gate is not None and i == 1:
            assert gate.wait(5)                       # hält nach der ersten Zeile an, bis der Test weiterlässt
        reached.append(s)
        yield s
    if fail:
        raise RuntimeError("kaputt")


def test_runs_to_the_end_when_the_reader_stops():
    reached: list[str] = []
    gate = threading.Event()
    op = operations.start("update", "demo", _gen(["Dateien ersetzt", "Frontend gebaut", "Neustart angefordert"], reached, gate))
    first = next(operations.follow(op))
    assert first == ("line", "Dateien ersetzt")
    gate.set()                                        # Leser ist weg – der Ablauf muss trotzdem durchlaufen
    assert op.wait(5)
    assert reached == ["Dateien ersetzt", "Frontend gebaut", "Neustart angefordert"]
    assert op.done and op.error is None
    assert operations.current() is None


def test_error_is_reported_logged_and_frees_the_lock(caplog):
    op = operations.start("install", "demo", _gen(["a"], [], fail=True))
    assert op.wait(5)
    events = list(operations.follow(op))
    assert events == [("line", "a"), ("error", "kaputt")]
    assert "Modul-Operation fehlgeschlagen" in caplog.text
    assert operations.current() is None
    again = operations.start("install", "demo", _gen(["b"], []))
    assert again.wait(5) and list(operations.follow(again)) == [("line", "b"), ("done", None)]


def test_second_start_is_refused_while_one_runs():
    gate = threading.Event()
    reached: list[str] = []
    op = operations.start("update", "studio", _gen(["x", "y"], reached, gate))
    second = _gen(["nie"], reached)
    with pytest.raises(operations.OperationBusy) as exc:
        operations.start("update", "atelier", second)
    assert exc.value.kind == "update" and exc.value.module_id == "studio"
    second.close()
    gate.set()
    assert op.wait(5)
    assert "nie" not in reached                       # der abgewiesene Ablauf hat nichts getan
    late = operations.start("uninstall", "atelier", _gen(["z"], []))
    assert late.wait(5)


def test_late_reader_gets_all_lines_in_order():
    op = operations.start("update", "demo", _gen(["1", "2", "3"], []))
    assert op.wait(5)
    assert list(operations.follow(op)) == [("line", "1"), ("line", "2"), ("line", "3"), ("done", None)]
    assert list(operations.follow(op)) == [("line", "1"), ("line", "2"), ("line", "3"), ("done", None)]   # mehrfach lesbar


def test_busy_message_exists_in_de_and_en_without_terminal_hint():
    import json
    from pathlib import Path
    loc = Path(__file__).resolve().parents[2] / "frontend/src/i18n/locales"
    for lang in ("de", "en"):
        text = json.loads((loc / lang / "errors.json").read_text(encoding="utf-8")).get("module_operation_busy", "")
        assert "{{module}}" in text, lang
        assert not any(w in text.lower() for w in ("terminal", "sudo", "systemctl", "update.sh", "install.conf"))


def test_worker_is_a_daemon_thread():
    """Der Ablauf darf das Beenden des Dienstes (Neustart) nicht aufhalten."""
    gate = threading.Event()
    seen: list[bool] = []

    def gen():
        seen.append(threading.current_thread().daemon)
        yield "x"
        assert gate.wait(5)
    op = operations.start("update", "demo", gen())
    try:
        for t in threading.enumerate():
            if t.name == "module-update-demo":
                assert t.daemon
                break
        else:
            raise AssertionError("kein Thread module-update-demo")
    finally:
        gate.set()
        assert op.wait(5)
    assert seen == [True]
