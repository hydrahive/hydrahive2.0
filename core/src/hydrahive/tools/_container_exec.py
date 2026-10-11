"""Befehle in Containern für den Harakiri-Schutz (docs/specs/harakiri-confirm-noise.md, Punkt 2).

`incus exec <ct> -- cat /etc/sudoers.d/x` liest im Container, nicht auf dem Host.
Der Schutz soll dafür nicht nachfragen. Ausnahmen:
- HydraHives eigene Container (ENV `HH_PROTECTED_CONTAINERS`), dort bleibt alles wie bisher;
- alles, was die Host-Shell selbst ausführt: `$( )`, Backticks, `<( )` außerhalb von
  einfachen Quotes (dann keine Ausnahme), Umleitungen (prüft der Aufrufer weiter).
Ein Containername aus einer Variable (`$c`) gilt als unbekannt → keine Ausnahme.
"""
from __future__ import annotations

import os
import re

from hydrahive.tools._shell_heredoc import runs_shell
from hydrahive.tools._shell_lex import mask_quotes, split_top_level, words

# ENV direkt gelesen (wie HH_BASE_DIR in default_protected): der Schutz läuft pro
# Aufruf und soll eine geänderte Liste ohne Neustart sehen.
_DEFAULT_PROTECTED = "hydrahive2-stt,hydrahive2-tts"
_CLIS = frozenset({"incus", "lxc"})
_VALUE_OPTS = frozenset({"--cwd", "--env", "--group", "--user", "--mode", "--project"})
_LEAD = frozenset({"sudo", "doas", "env", "nice", "nohup", "time", "command",
                   "do", "then", "else", "if", "elif", "while", "until", "{", "!"})
_REDIR = re.compile(r"(<|>>?)\s*([^\s;|&><)`]+)")


def protected_containers() -> frozenset[str]:
    raw = os.environ.get("HH_PROTECTED_CONTAINERS", _DEFAULT_PROTECTED)
    return frozenset(n.strip() for n in raw.split(",") if n.strip())


def _host_substitution(seg: str) -> bool:
    """`$( )`, Backticks, `<( )`/`>( )` außerhalb einfacher Quotes → führt der Host aus."""
    q: str | None = None
    i, n = 0, len(seg)
    while i < n:
        c = seg[i]
        if q == "'":
            q = None if c == "'" else q
        elif c == "\\":
            i += 2
            continue
        elif c == '"':
            q = None if q == '"' else '"'
        elif c == "'" and q is None:
            q = "'"
        elif c == "`" or (c in "$<>" and seg.startswith("(", i + 1)):
            return True
        i += 1
    return False


def _skip_lead(ws: list[str]) -> list[str]:
    while ws:
        if ws[0] in _LEAD:
            ws = ws[1:]
        elif ws[0] == "timeout" and len(ws) > 1:
            ws = ws[1:]
            while ws and ws[0].startswith("-"):
                ws = ws[2:] if ws[0] in ("-s", "-k") else ws[1:]
            ws = ws[1:]  # Dauer
        else:
            break
    return ws


def exempt_container(seg: str) -> str | None:
    """Containername, wenn `seg` ein `incus|lxc exec` in einen nicht geschützten
    Container ist und der Host nichts davon selbst ausführt. Sonst None."""
    ws = _skip_lead(words(seg))
    if len(ws) < 3 or os.path.basename(ws[0]) not in _CLIS or ws[1] != "exec":
        return None
    i = 2
    while i < len(ws) and ws[i].startswith("-"):
        if ws[i] == "--":
            return None
        i += 2 if ws[i] in _VALUE_OPTS else 1
    if i >= len(ws):
        return None
    name = ws[i].split(":", 1)[-1]
    if not name or "$" in name or "`" in name or name in protected_containers():
        return None
    return None if _host_substitution(seg) else name


def host_redirect_targets(seg: str) -> list[str]:
    """Ziele von Umleitungen außerhalb von Quotes – die öffnet die Host-Shell selbst."""
    masked = mask_quotes(seg)
    return [m.group(2) for m in _REDIR.finditer(seg) if masked[m.start()] == seg[m.start()]]


def runs_shell_on_host(line: str) -> bool:
    """Für strip_heredocs: Heredoc-Inhalt in einen freien Container ist Container-Inhalt."""
    return any(runs_shell(seg) for seg in split_top_level(line) if exempt_container(seg) is None)
