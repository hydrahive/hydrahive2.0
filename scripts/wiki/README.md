# Wiki und PDF-Handbuch

Gebaut wird automatisch von `.github/workflows/wiki.yml` (Push auf `main` mit Hilfe-Änderung, täglich, von Hand).
Ziel: `hydrahive2-modules/ziele/wiki-automatik.md`.

- `pages.py` – Seiten, Titel, Bereiche und Quelle (Kern-Hilfe, Modul-Hilfe, Rahmentext). Neue Seite = eine Zeile hier.
- `build.py` – schreibt das Wiki, entfernt Seiten ohne Quelle, prüft Datenschutz (Abbruch bei Treffer).
- `pdf_html.py`, `pdf_print.py`, `handbuch.css` – PDF-Handbuch, abrufbar unter
  `https://github.com/hydrahive/hydrahive2.0/releases/download/handbuch/HydraHive-Handbuch.pdf`.
- `texts/` – Startseite, „Was ist HydraHive?“, Module/Themes und Fußzeile.

Texte der Seiten ändert man **in den Hilfe-Artikeln**, nicht im Wiki: Änderungen direkt im Wiki überschreibt der nächste Bau.

Lokal ausprobieren:
```bash
python3 scripts/wiki/build.py . ../hydrahive2-modules /tmp/wiki
GITHUB_TOKEN=$(gh auth token) python3 scripts/wiki/pdf_html.py /tmp/wiki /tmp/handbuch.html
python3 scripts/wiki/pdf_print.py /tmp/handbuch.html /tmp/HydraHive-Handbuch.pdf   # braucht playwright + chromium
```
