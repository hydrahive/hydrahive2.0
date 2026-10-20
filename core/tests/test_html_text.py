"""Lesbarer Text statt HTML für fetch_url(format="text") (Spec websuche-kostenlos §6).

Anlass: Beim Borncity-Artikel vom 20.10.2026 lieferte fetch_url rund 190.000 Zeichen HTML samt CSS und JS,
der Artikel selbst war ein Bruchteil. Das kostet unnötig Token.
"""
from __future__ import annotations

from hydrahive.tools import _html_text as ht

_NOISE = "x" * 4000

ARTICLE_PAGE = f"""<!DOCTYPE html><html lang="de"><head>
<meta charset="UTF-8"><title>AFD-Leak; 421.179 interne E-Mails abgezogen – Borns IT-Blog</title>
<meta property="og:title" content="AFD-Leak; 421.179 interne E-Mails abgezogen">
<meta property="article:published_time" content="2026-10-20T00:22:01+00:00">
<style>.native-ad {{ margin: 20px; }} {_NOISE}</style>
<script>window.dataLayer = window.dataLayer || []; var secret = "{_NOISE}";</script>
</head><body>
<div id="header"><nav><ul><li><a href="/">Start</a></li><li><a href="/about">Impressum</a></li></ul></nav></div>
<aside>Werbung: Jetzt herunterladen</aside>
<article>
  <h1 class="entry-title">AFD-Leak; 421.179 interne E-Mails abgezogen</h1>
  <p>Die Mail-Server der AFD wurden über eine gravierende Sicherheitslücke gehackt.</p>
  <script>document.write("{_NOISE}")</script>
  <h2>E-Mail-Archiv abgezogen</h2>
  <p>Die Partei hat den Vorfall &amp; die Echtheit <a href="https://www.bild.de/x">gegenüber Bild</a> teils bestätigt.</p>
  <ul><li>Punkt eins</li><li>Punkt   zwei</li></ul>
</article>
<form><input name="comment"><button>Absenden</button></form>
<footer>© Günter Born</footer>
</body></html>"""


def test_article_text_without_scripts_styles_navigation():
    out = ht.extract(ARTICLE_PAGE)
    text = out["text"]
    assert "# AFD-Leak; 421.179 interne E-Mails abgezogen" in text
    assert "## E-Mail-Archiv abgezogen" in text
    assert "über eine gravierende Sicherheitslücke gehackt." in text
    assert "Die Partei hat den Vorfall & die Echtheit gegenüber Bild teils bestätigt." in text
    for noise in ("dataLayer", "native-ad", "document.write", "xxxx", "Impressum",
                  "Werbung", "Absenden", "Günter Born"):
        assert noise not in text
    assert "https://www.bild.de" not in text
    assert len(text) < len(ARTICLE_PAGE) * 0.10


def test_list_items_and_whitespace_are_tidy():
    text = ht.extract(ARTICLE_PAGE)["text"]
    assert "Punkt eins\nPunkt zwei" in text
    assert "\n\n\n" not in text
    assert "  " not in text


def test_title_and_date_from_meta():
    out = ht.extract(ARTICLE_PAGE)
    assert out["title"] == "AFD-Leak; 421.179 interne E-Mails abgezogen"
    assert out["published"] == "2026-10-20T00:22:01+00:00"


def test_title_falls_back_to_title_tag_and_time_element():
    page = ("<html><head><title>Nur Titel</title></head><body><main>"
            "<time datetime='2026-10-19'>gestern</time><p>Inhalt</p></main></body></html>")
    out = ht.extract(page)
    assert out["title"] == "Nur Titel"
    assert out["published"] == "2026-10-19"


def test_article_wins_over_main_and_body():
    page = ("<html><body><p>Rand</p><main><p>Haupt</p><article><p>Artikel</p></article></main>"
            "</body></html>")
    assert ht.extract(page)["text"] == "Artikel"


def test_main_wins_over_body():
    page = "<html><body><p>Rand</p><main><p>Haupt</p></main></body></html>"
    assert ht.extract(page)["text"] == "Haupt"


def test_broken_html_without_body_does_not_crash():
    out = ht.extract("<p>offen <b>fett <i>kursiv</p> <script>kaputt")
    assert "offen fett kursiv" in out["text"]
    assert "kaputt" not in out["text"]
    assert out["title"] is None
    assert out["published"] is None


def test_default_headers_set_browser_identity():
    h = ht.default_headers({})
    assert h["User-Agent"].startswith("Mozilla/5.0")
    assert "text/html" in h["Accept"]
    assert h["Accept-Language"].startswith("de-DE")


def test_default_headers_never_override_caller_any_case():
    given = {"user-agent": "MeinBot/1.0", "ACCEPT": "application/json", "X-Extra": "1"}
    h = ht.default_headers(given)
    assert h["user-agent"] == "MeinBot/1.0"
    assert h["ACCEPT"] == "application/json"
    assert h["X-Extra"] == "1"
    assert "User-Agent" not in h
    assert "Accept" not in h
    assert h["Accept-Language"].startswith("de-DE")


def test_navigation_header_footer_removed_even_without_article():
    page = ("<html><body><header>Kopf</header><nav><a href='/'>Start</a></nav>"
            "<div><p>Nur Inhalt</p></div><aside>Rand</aside><footer>Fuß</footer></body></html>")
    assert ht.extract(page)["text"] == "Nur Inhalt"
