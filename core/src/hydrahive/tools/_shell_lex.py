"""Kleine Shell-Zerlegung für den Harakiri-Schutz (tools/_protected_paths.py).

Bewusst kein vollständiger Shell-Parser: Der Schutz ist ein Stolperdraht gegen
Unfälle, keine Mauer. Hier liegt nur, was die Prüfungen gemeinsam brauchen.
"""
from __future__ import annotations


def split_top_level(cmd: str) -> list[str]:
    """Splittet an `;`, `&`, `|`, Newline — aber nur AUSSERHALB von Quotes.

    Ersetzt das quote-blinde `re.split`: `ssh host 'a && b'` bleibt ein Segment,
    statt in lokal aussehende `a`/`b` zu zerfallen.
    """
    segs: list[str] = []
    buf: list[str] = []
    q: str | None = None
    i, n = 0, len(cmd)
    while i < n:
        c = cmd[i]
        if q is not None:
            buf.append(c)
            if c == "\\" and q == '"' and i + 1 < n:
                buf.append(cmd[i + 1])
                i += 2
                continue
            if c == q:
                q = None
            i += 1
            continue
        if c in ("'", '"'):
            q = c
            buf.append(c)
        elif c == "\\" and i + 1 < n:
            buf.append(c)
            buf.append(cmd[i + 1])
            i += 2
            continue
        elif c in ";&|\n":
            segs.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    if buf:
        segs.append("".join(buf))
    return segs


def mask_quotes(s: str) -> str:
    """Ersetzt gequotete Inhalte durch Leerzeichen (Quote-Zeichen bleiben).

    So matcht der Redirect-Scan nur Redirections ausserhalb von Quotes —
    `echo x > /etc/y` innerhalb von `ssh host '...'` ist ein Remote-Redirect.
    """
    out: list[str] = []
    q: str | None = None
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if q is not None:
            if c == "\\" and q == '"' and i + 1 < n:
                out.append("  ")
                i += 2
                continue
            if c == q:
                q = None
                out.append(c)
            else:
                out.append(" ")
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            out.append(c)
            out.append(s[i + 1])
            i += 2
            continue
        if c in ("'", '"'):
            q = c
        out.append(c)
        i += 1
    return "".join(out)
