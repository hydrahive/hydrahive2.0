"""Heredoc-Inhalt für den Harakiri-Schutz ausblenden (docs/specs/harakiri-confirm-noise.md, 1c).

`cat > test.py <<'EOF' … EOF` schreibt Text in eine Datei, der Inhalt ist kein
Shell-Befehl. Ohne das Ausblenden prüft der Schutz Python-Code wie Shell-Zeilen
(`r.key` → „Schlüsseldatei“, Fehlalarm 07.10./09.10.2026).

Geprüft bleibt der Inhalt, wenn in der Zeile mit dem `<<` ein Programm steht, das
Shell-Text ausführt (bash, ssh, sudo …). Im Zweifel bleibt der Text stehen:
nicht abgeschlossene Heredocs werden nicht ausgeblendet.
"""
from __future__ import annotations

import os
import re
from collections.abc import Callable

_SHELL_RUNNERS = frozenset({
    "bash", "sh", "zsh", "dash", "ksh", "mksh", "fish", "busybox",
    "su", "sudo", "doas", "runuser", "chroot", "nsenter", "unshare",
    "ssh", "at", "batch", "crontab", "source", "eval",
})
_WORD = re.compile(r"[^\s;|&()<>`]+")
_WORD_END = " \t\n;|&()<>`"


def runs_shell(line: str) -> bool:
    return any(os.path.basename(w.strip("'\"")) in _SHELL_RUNNERS for w in _WORD.findall(line))


def _read_marker(s: str, j: int) -> tuple[str, int]:
    """Ende-Marker ab Position j, Quotes und Backslashes fallen weg ('EOF', \\EOF, E"O"F)."""
    buf: list[str] = []
    n = len(s)
    while j < n and s[j] not in _WORD_END:
        c = s[j]
        if c in "'\"":
            k = s.find(c, j + 1)
            if k < 0:
                return "", j
            buf.append(s[j + 1:k])
            j = k + 1
        elif c == "\\" and j + 1 < n:
            buf.append(s[j + 1])
            j += 2
        else:
            buf.append(c)
            j += 1
    return "".join(buf), j


def _body_end(cmd: str, start: int, markers: list[tuple[str, bool]]) -> int | None:
    """Index hinter der letzten Ende-Zeile, oder None wenn ein Marker fehlt."""
    pos = start
    for marker, tabs in markers:
        while True:
            if pos >= len(cmd):
                return None
            nl = cmd.find("\n", pos)
            line_end = len(cmd) if nl < 0 else nl
            line = cmd[pos:line_end]
            pos = line_end + 1
            if (line.lstrip("\t") if tabs else line) == marker:
                break
    return min(pos, len(cmd))


def strip_heredocs(cmd: str, shell_runs: Callable[[str], bool] = runs_shell) -> str:
    """Befehl ohne Heredoc-Inhalt (die Zeile mit `<<` und alles danach bleiben).

    `shell_runs(zeile)`: True, wenn auf dem Host etwas den Inhalt als Shell-Text
    ausführt – dann bleibt er stehen und wird geprüft."""
    out: list[str] = []
    last = line_start = i = 0
    n = len(cmd)
    q: str | None = None
    markers: list[tuple[str, bool]] = []
    while i < n:
        c = cmd[i]
        if q is not None:
            if c == "\\" and q == '"':
                i += 2
                continue
            q = None if c == q else q
            i += 1
            continue
        if c == "\\":
            i += 2
            continue
        if c in "'\"":
            q = c
        elif c == "#" and (i == 0 or cmd[i - 1] in " \t\n;&|("):
            nl = cmd.find("\n", i)
            i = n if nl < 0 else nl
            continue
        elif cmd.startswith("<<", i):
            # `$((1<<2))` ist ein Bit-Shift. Here-Strings (`<<<`) brauchen keine
            # Sonderregel: _read_marker hört bei `<` auf, der Marker bleibt leer.
            head = cmd[line_start:i]
            if head.count("((") > head.count("))"):
                i += 2
                continue
            j = i + 2
            tabs = j < n and cmd[j] == "-"
            j += 1 if tabs else 0
            while j < n and cmd[j] in " \t":
                j += 1
            marker, j = _read_marker(cmd, j)
            if marker:
                markers.append((marker, tabs))
            i = max(j, i + 2)
            continue
        elif c == "\n":
            if markers:
                end = _body_end(cmd, i + 1, markers)
                if end is not None:
                    if not shell_runs(cmd[line_start:i]):
                        out.append(cmd[last:i + 1])
                        last = end
                    i = end
                    line_start = end
                    markers = []
                    continue
                markers = []
            line_start = i + 1
        i += 1
    out.append(cmd[last:])
    return "".join(out)
