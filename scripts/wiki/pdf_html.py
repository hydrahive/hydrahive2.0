"""Wiki-Ordner → ein HTML-Dokument fürs PDF-Handbuch (Ziel wiki-automatik.md, WK4).

Reihenfolge und Bereiche aus _Sidebar.md. Markdown → HTML über die GitHub-API (gfm, wie im Wiki).
Wiki-Links [[Text|Seite]] werden zu Sprüngen im Dokument. Aufruf:
  python3 scripts/wiki/pdf_html.py <wiki-ordner> <ausgabe.html>   (Token aus GITHUB_TOKEN/GH_TOKEN)
"""
from __future__ import annotations

import datetime
import html
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

LINK = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")
CSS = (Path(__file__).resolve().parent / "handbuch.css")


def slug(page: str) -> str:
    return "p-" + re.sub(r"[^a-z0-9]+", "-", page.lower()).strip("-")


def sections(sidebar: str) -> list[tuple[str, list[tuple[str, str]]]]:
    out: list[tuple[str, list[tuple[str, str]]]] = []
    for line in sidebar.splitlines():
        m = re.match(r"\*\*(.+?)\*\*\s*$", line.strip())
        if m and "[[" not in line:
            out.append((m.group(1), []))
            continue
        if out:
            for text, page in LINK.findall(line):
                out[-1][1].append((text.strip(), (page or text).strip()))
    return out


def wikilinks(md: str, known: set[str]) -> str:
    def rep(m: re.Match) -> str:
        text, page = m.group(1).strip(), (m.group(2) or m.group(1)).strip()
        return f"[{text}](#{slug(page)})" if page in known else text
    return LINK.sub(rep, md)


def gfm(md: str, token: str) -> str:
    req = urllib.request.Request(
        "https://api.github.com/markdown", method="POST",
        data=json.dumps({"text": md, "mode": "gfm", "context": "hydrahive/hydrahive2.0"}).encode(),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode()


def document(wiki: Path, render, today: str) -> str:
    secs = sections((wiki / "_Sidebar.md").read_text(encoding="utf-8"))
    order = ["Home"] + [p for _, items in secs for _, p in items if (wiki / f"{p}.md").exists()]
    known = set(order)
    parts = []
    for page in order:
        body = render(wikilinks((wiki / f"{page}.md").read_text(encoding="utf-8"), known))
        parts.append(f'<section class="page" id="{slug(page)}">{body}</section>')
    toc = "".join(
        f"<h3>{html.escape(name)}</h3><ul>"
        + "".join(f'<li><a href="#{slug(p)}">{html.escape(t)}</a></li>' for t, p in items if p in known)
        + "</ul>" for name, items in secs)
    return (f'<!doctype html><html lang="de"><head><meta charset="utf-8"><title>HydraHive-Handbuch</title>'
            f"<style>{CSS.read_text(encoding='utf-8')}</style></head><body>"
            f'<div class="cover"><h1>🐝 HydraHive-Handbuch</h1><p>Stand: {html.escape(today)}<br>'
            f"Quelle: github.com/hydrahive/hydrahive2.0/wiki</p>"
            f"<p><small>Beta – automatisch aus den Hilfe-Artikeln gebaut.</small></p></div>"
            f'<div class="toc"><h1>Inhalt</h1>{toc}</div>{"".join(parts)}</body></html>')


def main(argv: list[str]) -> int:
    wiki, out = Path(argv[1]), Path(argv[2])
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    doc = document(wiki, lambda md: gfm(md, token), datetime.date.today().strftime("%d.%m.%Y"))
    left = LINK.findall(re.sub(r"<[^>]+>", "", doc))
    if left:
        print(f"Unaufgelöste Wiki-Links: {left[:5]}")
        return 1
    out.write_text(doc, encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
