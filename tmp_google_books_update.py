#!/usr/bin/env python3
"""
Google Books Metadaten-Updater
Aktualisiert Bücher mit Status != 'komplett' via Google Books API.
Ersetzt OpenLibrary (7% Treffer bei deutschen Büchern).
"""

import json
import os
import sys
import time
from datetime import datetime
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import URLError, HTTPError

# ── Pfade ──────────────────────────────────────────────────────────────────────
EPUB_SCAN_PATH = (
    "/var/lib/hydrahive2/workspaces/projects/"
    "019e1e35-9b1a-72e7-b421-91162a3915ae/"
    "Bibliothek/system/logs/epub_scan.json"
)
KATALOG_PATH = (
    "/var/lib/hydrahive2/workspaces/projects/"
    "019e1e35-9b1a-72e7-b421-91162a3915ae/"
    "Bibliothek/system/katalog/buecher.json"
)
LOG_PATH = (
    "/var/lib/hydrahive2/workspaces/specialists/"
    "5266ba3b-8931-44b9-9ab3-da1b4570e53a/google_books_update.log"
)

# ── Konfiguration ──────────────────────────────────────────────────────────────
SAVE_INTERVAL = 25
REQUEST_DELAY = 1.2   # Google Books: >1 req/s ohne API-Key sicher
TIMEOUT       = 12
MAX_RETRIES   = 3

# Optionaler API-Key: GOOGLE_BOOKS_API_KEY=... python3 google_books_update.py
# Ohne Key: 1000 req/day anonymes Limit; mit Key: 1000 req/day Gratis-Tier.
# Kostenlosen Key holen: https://console.developers.google.com/ → Books API aktivieren
GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY", "")

_OPENER = build_opener(HTTPRedirectHandler())
_HEADERS = {"User-Agent": "HydraHive-LibraryCatalog/1.0 (hydrahive@localhost)"}
_logfile = None


def log(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if _logfile:
        _logfile.write(line + "\n")
        _logfile.flush()


def fetch_json(url: str, retries: int = MAX_RETRIES) -> dict | None:
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=_HEADERS)
            with _OPENER.open(req, timeout=TIMEOUT) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
                return None
        except HTTPError as e:
            if e.code == 404:
                return None
            if e.code in (429, 503):
                backoff = 30 * (attempt + 1)  # 30s, 60s, 90s
                log(f"  ⚠ HTTP {e.code} — warte {backoff}s …")
                time.sleep(backoff)
            elif attempt < retries:
                time.sleep(3)
        except (URLError, Exception):
            if attempt < retries:
                time.sleep(3)
    return None


def get_google_books_data(isbn: str) -> dict | None:
    key_param = f"&key={GOOGLE_BOOKS_API_KEY}" if GOOGLE_BOOKS_API_KEY else ""
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&maxResults=1{key_param}"
    data = fetch_json(url)
    if not data:
        return None

    items = data.get("items", [])
    if not items:
        return None

    info = items[0].get("volumeInfo", {})
    titel = info.get("title", "")
    if not titel:
        return None

    subtitle = info.get("subtitle", "")
    if subtitle:
        titel = f"{titel}: {subtitle}"

    autoren = info.get("authors", [])
    autor = autoren[0] if autoren else ""

    publishers = info.get("publisher", "")
    verlag = publishers if isinstance(publishers, str) else ""

    published = info.get("publishedDate", "")
    jahr = None
    if published and len(published) >= 4:
        try:
            jahr = int(published[:4])
        except ValueError:
            pass

    image_links = info.get("imageLinks", {})
    cover_url = image_links.get("thumbnail", "")
    # HTTPS erzwingen (Google liefert manchmal http://)
    if cover_url.startswith("http://"):
        cover_url = cover_url.replace("http://", "https://", 1)

    return {
        "titel": titel,
        "autor": autor,
        "jahr": jahr,
        "verlag": verlag,
        "cover_url": cover_url,
        "isbn": isbn,
    }


def save_katalog(katalog: dict, path: str) -> None:
    tmp_path = path + ".tmp"
    katalog["metadata"]["letzte_aenderung"] = datetime.now().isoformat()
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(katalog, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def main():
    global _logfile
    _logfile = open(LOG_PATH, "w", encoding="utf-8")

    log("=" * 60)
    log("Google Books Metadaten-Updater gestartet")
    log("=" * 60)

    log("Lade ISBN-Map …")
    with open(EPUB_SCAN_PATH, encoding="utf-8") as f:
        isbn_map: dict[str, str] = json.load(f)
    log(f"  → {len(isbn_map)} Einträge in der ISBN-Map")

    log("Lade Katalog …")
    with open(KATALOG_PATH, encoding="utf-8") as f:
        katalog = json.load(f)
    buecher: list[dict] = katalog.get("buecher", [])
    log(f"  → {len(buecher)} Bücher im Katalog")

    # Kandidaten: Status != 'komplett' (fehlgeschlagen + unbehandelt)
    kandidaten = [
        (idx, b)
        for idx, b in enumerate(buecher)
        if b.get("metadaten_status") != "komplett"
    ]
    log(f"  → {len(kandidaten)} Bücher mit Status ≠ 'komplett'")

    mit_isbn = sum(
        1 for _, b in kandidaten
        if isbn_map.get(b.get("dateiname", ""))
    )
    log(f"  → {mit_isbn} davon haben eine ISBN")

    isbn_cache: dict[str, dict | None] = {}
    aktualisiert = kein_isbn = api_fehler = gespeichert_bei = 0
    total = len(kandidaten)

    for lauf_nr, (idx, buch) in enumerate(kandidaten, start=1):
        dateiname = buch.get("dateiname", "")
        isbn = isbn_map.get(dateiname)

        if lauf_nr % 50 == 0 or lauf_nr == 1:
            log(f"  Fortschritt: {lauf_nr}/{total} | "
                f"✓ {aktualisiert} | ✗ ISBN fehlt: {kein_isbn} | "
                f"✗ API-Fehler: {api_fehler}")

        if not isbn:
            kein_isbn += 1
            buecher[idx]["metadaten_status"] = "fehlgeschlagen"
            continue

        if isbn not in isbn_cache:
            time.sleep(REQUEST_DELAY)
            isbn_cache[isbn] = get_google_books_data(isbn)

        gb_data = isbn_cache[isbn]

        if gb_data is None:
            api_fehler += 1
            buecher[idx]["metadaten_status"] = "fehlgeschlagen"
            continue

        buecher[idx]["google_books"] = {
            **gb_data,
            "aktualisiert_am": datetime.now().isoformat(),
        }
        buecher[idx]["metadaten_status"] = "komplett"
        aktualisiert += 1

        if aktualisiert - gespeichert_bei >= SAVE_INTERVAL:
            log(f"  💾 Zwischenspeicherung nach {aktualisiert} Aktualisierungen …")
            save_katalog(katalog, KATALOG_PATH)
            gespeichert_bei = aktualisiert

    log("💾 Finales Speichern …")
    katalog["metadata"]["letzte_gb_abfrage"] = datetime.now().isoformat()
    save_katalog(katalog, KATALOG_PATH)

    log("=" * 60)
    log("ABSCHLUSSBERICHT")
    log("=" * 60)
    log(f"  Kandidaten gesamt:          {total}")
    log(f"  ✅ Erfolgreich aktualisiert: {aktualisiert}")
    log(f"  ⚠️  Kein ISBN-Match:          {kein_isbn}")
    log(f"  ❌ API-Fehler (Google Books): {api_fehler}")
    log(f"  Unique ISBNs abgefragt:     {len(isbn_cache)}")
    log("=" * 60)

    _logfile.close()
    return aktualisiert


if __name__ == "__main__":
    try:
        count = main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n[ABBRUCH] Durch Benutzer unterbrochen.", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"\n[FEHLER] {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(2)
