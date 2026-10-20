"""Modul-Abläufe (Install, Update, Deinstallation) laufen in einem eigenen Thread bis zum Ende.

Vorher hat der SSE-Stream den Installer-Generator direkt durchlaufen. Trennte der Browser die Verbindung, blieb der
Ablauf mittendrin stehen: Dateien ersetzt, Frontend gebaut, aber kein Neustart (docs/specs/modul-update-unabhaengig-vom-browser.md).
Jetzt liest ein Daemon-Thread den Generator vollständig; der Stream ist nur noch Zuschauer (`follow`).
Es läuft höchstens ein Ablauf gleichzeitig (`OperationBusy`).
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_current: Operation | None = None


class OperationBusy(RuntimeError):
    def __init__(self, kind: str, module_id: str) -> None:
        super().__init__(f"{kind} {module_id} läuft schon")
        self.kind, self.module_id = kind, module_id


@dataclass
class Operation:
    kind: str
    module_id: str
    lines: list[str] = field(default_factory=list)
    done: bool = False
    error: str | None = None
    _cond: threading.Condition = field(default_factory=threading.Condition, repr=False)

    @property
    def finished(self) -> bool:
        return self.done or self.error is not None

    def wait(self, timeout: float | None = None) -> bool:
        with self._cond:
            return self._cond.wait_for(lambda: self.finished, timeout)


def current() -> Operation | None:
    """Der gerade laufende Ablauf (oder None)."""
    return _current


def _run(op: Operation, gen: Iterator[str]) -> None:
    global _current
    try:
        for line in gen:
            with op._cond:
                op.lines.append(line)
                op._cond.notify_all()
        with op._cond:
            op.done = True
    except Exception as exc:
        logger.exception("Modul-Operation fehlgeschlagen (%s %s)", op.kind, op.module_id)
        with op._cond:
            op.error = str(exc)
    finally:
        with _lock:                                   # erst frei, wenn der Ablauf wirklich zu Ende ist
            if _current is op:
                _current = None
        with op._cond:
            if not op.finished:                       # z. B. BaseException – Leser nicht hängen lassen
                op.error = "abgebrochen"
            op._cond.notify_all()


def start(kind: str, module_id: str, gen: Iterator[str]) -> Operation:
    """Startet den Ablauf im Hintergrund. Läuft schon einer: `OperationBusy` (der Generator wird nicht angefasst)."""
    global _current
    with _lock:
        if _current is not None:
            raise OperationBusy(_current.kind, _current.module_id)
        op = _current = Operation(kind, module_id)
    threading.Thread(target=_run, args=(op, gen), name=f"module-{kind}-{module_id}", daemon=True).start()
    return op


def follow(op: Operation) -> Iterator[tuple[str, str | None]]:
    """Alle Zeilen des Ablaufs (auch die schon vergangenen), dann ("done", None) oder ("error", text)."""
    i = 0
    while True:
        with op._cond:
            op._cond.wait_for(lambda: len(op.lines) > i or op.finished)
            new, finished, error = op.lines[i:], op.finished, op.error
        for line in new:
            yield "line", line
        i += len(new)
        if finished and i >= len(op.lines):
            yield ("error", error) if error is not None else ("done", None)
            return
