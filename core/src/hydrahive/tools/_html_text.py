"""Lesbarer Text aus HTML und Browser-Header für fetch_url (Spec docs/specs/websuche-kostenlos.md §6).

Nur Standardbibliothek (html.parser), keine neue Abhängigkeit. Bewusst einfach: Artikel- und
Nachrichtenseiten. Seiten, die erst per JavaScript entstehen, bleiben ein Fall für web_browser.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_DEFAULTS = {
    "User-Agent": BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

_SKIP = {"script", "style", "noscript", "svg", "template", "iframe", "nav", "footer",
         "header", "aside", "form", "button", "select", "textarea"}
_SKIP_ROLES = {"navigation", "banner", "contentinfo", "complementary", "search"}  # = nav/header/footer/aside
_VOID = {"br", "img", "input", "meta", "link", "hr", "source", "wbr", "area", "base", "col", "embed", "track"}
_BLOCK = {"p", "div", "li", "tr", "br", "section", "blockquote", "pre", "table", "ul", "ol",
          "dd", "dt", "figcaption", "h1", "h2", "h3", "h4", "h5", "h6"}
_LINE = {"li", "tr", "dt", "dd"}          # nur Zeilenumbruch davor, keine Leerzeile dazwischen
_CONTAINERS = ("article", "main", "body")


def default_headers(given: dict) -> dict:
    """Ergänzt Browser-Header, die der Aufrufer nicht selbst gesetzt hat (Name egal in welcher Schreibweise)."""
    have = {k.lower() for k in given}
    out = dict(given)
    for name, value in _DEFAULTS.items():
        if name.lower() not in have:
            out[name] = value
    return out


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.open: list[str] = []
        self.parts: dict[str, list[str]] = {c: [] for c in _CONTAINERS}
        self.parts["all"] = []
        self.meta: dict[str, str] = {}
        self.title_tag: list[str] = []
        self.time_attr: str | None = None

    def _emit(self, s: str) -> None:
        targets = ["all"] + [c for c in _CONTAINERS if c in self.open]
        for t in targets:
            self.parts[t].append(s)

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "meta":
            key = a.get("property") or a.get("name")
            if key and a.get("content"):
                self.meta.setdefault(key.lower(), a["content"].strip())
            return
        if tag == "time" and self.time_attr is None and a.get("datetime"):
            self.time_attr = a["datetime"].strip()
        if self.skip_depth or tag in _SKIP or a.get("role", "").lower() in _SKIP_ROLES:
            if tag not in _VOID:
                self.skip_depth += 1
            return
        if tag in _VOID:
            if tag == "br":
                self._emit("\n")
            return
        self.open.append(tag)
        if tag in _BLOCK:
            self._emit("\n")
        if re.fullmatch(r"h[1-6]", tag):
            self._emit("#" * int(tag[1]) + " ")

    def handle_endtag(self, tag):
        if self.skip_depth:
            if tag not in _VOID:
                self.skip_depth -= 1
            return
        if tag in self.open:
            while self.open:
                if self.open.pop() == tag:
                    break
            if tag in _BLOCK and tag not in _LINE:
                self._emit("\n")

    def handle_data(self, data):
        if self.skip_depth:
            return
        if "title" in self.open:
            self.title_tag.append(data)
            return
        self._emit(data)


def _tidy(parts: list[str]) -> str:
    text = "".join(parts)
    lines = [re.sub(r"[ \t\r\f\v\u00a0]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract(html: str) -> dict:
    """{"text", "title", "published"} – Text aus <article>, sonst <main>, sonst <body>, sonst allem."""
    p = _Collector()
    try:
        p.feed(html)
        p.close()
    except Exception:  # html.parser wirft praktisch nie – kaputtes HTML liefert dann Teiltext
        pass
    text = ""
    for container in (*_CONTAINERS, "all"):
        text = _tidy(p.parts[container])
        if text:
            break
    title = p.meta.get("og:title") or (_tidy(p.title_tag) or None)
    published = p.meta.get("article:published_time") or p.time_attr
    return {"text": text, "title": title, "published": published}
