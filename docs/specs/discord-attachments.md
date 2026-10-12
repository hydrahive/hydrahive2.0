# Feature-Spec: Bilder an Discord-Nachrichten (discord_post / discord_reply)

Stand: 12.10.2026 · Erweitert `discord-agent-tools.md` (dort war „Dateianhänge“ ausdrücklich nicht in Scope).

## 1. Problem

Agenten pflegen Handbücher in Discord-Foren. Die Werkzeuge können nur Text senden. Grafiken und Screenshots
(z. B. `generated/hydra-grafiken/*.png`) lassen sich nicht anhängen; der einzige Weg wäre ein direkter
API-Aufruf am Werkzeug und an den Freigaben vorbei.

## 2. Scope

### In Scope
- Neuer optionaler Parameter `images` (Liste von Pfaden) für **`discord_post`** und **`discord_reply`**.
- Bilder hängen an der **ersten** gesendeten Nachricht (bei Forum-Beiträgen: der Eröffnung).
- Nur Bildformate: `png`, `jpg`/`jpeg`, `gif`, `webp`.

### Nicht in Scope
- Andere Dateitypen (PDF, Audio, Archive …) – bewusst nicht, siehe Sicherheit.
- Bilder per URL (kein Nachladen aus dem Netz, kein SSRF-Weg).
- Bilder bei `discord_edit` (Anhänge nachträglich ändern).
- Bilder aus verknüpften Projekten.

## 3. Sicherheit

Ein Anhang verlässt das System – die Regeln sind strenger als beim Lesen.

- **Nur eigener Arbeitsordner:** Pfad über `safe_path(ctx.workspace, …)` (Symlinks aufgelöst, `../` und absolute
  Pfade außerhalb abgelehnt). Keine verknüpften Projekte (`read_path`), kein Fallback.
- **Nur Bilder, am Inhalt erkannt:** Endung aus der Erlaubnisliste UND Magic Bytes passend
  (PNG `\x89PNG`, JPEG `\xFF\xD8\xFF`, GIF `GIF87a/GIF89a`, WebP `RIFF….WEBP`). Eine umbenannte Datei mit
  Secrets wird abgelehnt.
- **Geschützte Pfade:** dieselben Sperren wie die Shell-Gates (`.ssh/`, `*.key`, `*.pem`, `id_rsa` …) –
  greift zusätzlich, auch wenn eine solche Datei als Bild getarnt ist.
- **Grenzen:** höchstens **4 Bilder** je Aufruf, je Bild höchstens **8 MB** (Discord-Grenze ohne Boost),
  zusammen höchstens **24 MB**. Leere Dateien abgelehnt.
- **Dateiname im Upload:** nur der Basisname, auf `[A-Za-z0-9._-]` bereinigt (kein Pfad nach außen).
- Text läuft wie bisher durch `egress_scrub`; `NO_MASS_PINGS` bleibt.
- Fehler nennen den Pfad wie angegeben, nie den aufgelösten absoluten Pfad.
- Alle Prüfungen **vor** dem ersten Discord-Aufruf: entweder alles geht raus oder nichts.

## 4. Architektur

```
tools/discord_write.py              + images im Schema, _load_images(ctx, paths) → list[ImageFile]
tools/_discord_images.py   (neu)    Prüfung: safe_path, Schutzliste, Endung, Magic Bytes, Größen
communication/discord/ops_write.py  post/reply nehmen files: list[ImageFile]; erste Nachricht bekommt
                                    discord.File(io.BytesIO(data), filename=…)
```

`ImageFile` = `(filename: str, data: bytes)`. Die Discord-Schicht bekommt nur geprüfte Bytes, nie Pfade.

## 5. Akzeptanzkriterien

- [ ] `discord_post` in ein Forum mit 1–4 Bildern: Eröffnung trägt die Bilder.
- [ ] `discord_reply` mit Bildern: erste Antwort-Nachricht trägt die Bilder; bei aufgeteiltem Text nur die erste.
- [ ] Nur Bilder ohne Text geht (`text` darf leer sein, wenn `images` gesetzt).
- [ ] Abgelehnt mit verständlicher Meldung, **ohne** dass etwas gesendet wird: Pfad außerhalb, `../`, Symlink
      nach draußen, falsche Endung, falscher Inhalt (z. B. Text als `.png`), geschützter Pfad, > 4 Bilder,
      > 8 MB, Summe > 24 MB, leere oder fehlende Datei.
- [ ] Ohne `images` verhalten sich beide Werkzeuge exakt wie vorher.
- [ ] Live-Test: Handbuch-Beitrag mit den 4 HydraHive-Grafiken auf beiden Servern.
