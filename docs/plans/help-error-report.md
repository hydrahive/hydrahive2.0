# Plan: Fehlerbericht über den Hilfe-Assistenten (per E-Mail)

Status: **freigegeben** (Till 24.10.2026: „wir machen das über das eingetragene Konto, optional bei keinem Konto in
Mailprogramm öffnen und nem kleinen Link zu Mailzugang einrichten … der Rest passt so“). Task f3ac5dc2.

## Ziel

Meldet ein Nutzer dem Hilfe-Assistenten einen Fehler, liest der Assistent die **echten Fehlerdaten** der Installation
selbst aus (Fehlerprotokoll, Seite, Versionen, System) und schreibt daraus einen Bericht. Der Nutzer sieht den Bericht
und schickt ihn mit einem Klick an das Fehler-Postfach von HydraHive. So hängt die Fehlersuche nicht an einer vagen
Beschreibung wie „geht nicht“.

## Ablauf

1. Nutzer im Hilfe-Fenster: „Beim Senden kommt ein Fehler.“
2. Assistent ruft `error_report_prepare` auf. Das Werkzeug sammelt **auf dem Server** (nicht das Modell):
   - die letzten Einträge aus `errors_log` **dieses Nutzers** (höchstens 5, letzte 24 h; Fehlertext, Stelle, Quelle –
     schon geschwärzt) und nochmals durch `redaction.scrub` mit den Secrets des Nutzers;
   - aktuelle Seite (schon bereinigt, `helpdesk/_context.clean_path`), HydraHive-Version + Commit, Betriebssystem,
     Python-Version, installierte Module mit Version;
   - die Beschreibung des Nutzers in seinen Worten (vom Assistenten zusammengefasst, höchstens 1000 Zeichen).
   Das Werkzeug legt einen **Entwurf** an (Speicher des Dienstes, je Nutzer, 30 min gültig) und gibt dem Modell nur
   eine Kurzfassung + Entwurfs-ID zurück.
3. Das Hilfe-Fenster zeigt den Entwurf als **Karte**: Betreff, voller Text (scrollbar), Knopf **„Senden“**, Knopf
   **„Verwerfen“**. Der Text ist fest nach Vorlage gebaut (siehe unten); das Modell kann darin nur das Feld
   „Beschreibung“ füllen.
4. **Senden** (nur durch Klick des Nutzers, Route `POST /api/helpdesk/report/{id}/send`):
   - **Mailzugang eingerichtet** (System → Einstellungen → Mail, Host + Absender): Versand über genau dieses Konto,
     gleicher Weg wie `send_mail` (`communication.mail._transport.send_message`). Antwort „Gesendet“.
   - **Kein Mailzugang:** Knopf **„Im Mailprogramm öffnen“** (`mailto:` mit Empfänger, Betreff, Text; Text bei Bedarf
     gekürzt, voller Text zum Kopieren daneben) und ein kleiner Link **„Mailzugang einrichten“** → Systemeinstellungen
     (nur für Admins sichtbar; Nutzer sehen „Admin bitten, den Mailzugang einzurichten“).
5. Fehlerbericht ist nur möglich, wenn der Admin den globalen Schalter eingeschaltet hat.

## Schalter und Adresse

- `help_error_report_enabled` (bool) in `EDITABLE_SETTINGS`, Gruppe „Hilfe“, **Standard an**? → **Standard aus**
  wäre vorsichtiger, verhindert aber die Meldungen gerade bei den externen Nutzern, für die es gedacht ist. Weil
  jeder Bericht ohnehin erst nach Klick und mit sichtbarem Inhalt gesendet wird, ist der Standard **an**, der Admin
  kann ihn ausschalten. (Entscheidung offen für Till, siehe unten.)
- Zieladresse: Konstante `ERROR_REPORT_TO` im Kern, überschreibbar mit `HH_ERROR_REPORT_TO` (für Firmen, die
  Berichte selbst sammeln wollen). **Keine Zugangsdaten im Code** – gesendet wird immer über das Konto der
  Installation.

## Vorlage des Berichts (fest, nicht vom Modell)

```
Betreff: [HydraHive-Fehler] <error_type oder „Meldung“> – <Seite> – <Version>

Beschreibung (Nutzer):
<Text, max. 1000 Zeichen>

Seite: /mailbox
HydraHive: 2.0.0 (Commit 3311bf36)   System: Linux 6.x / macOS 27   Python: 3.12
Module: mailbox 0.7.1, storyteller 0.20.0, …

Fehler (letzte 24 h, dieses Nutzers, geschwärzt):
1) 2026-10-24 10:12  tool.crash  SMTPAuthenticationError
   Anmeldung abgelehnt: 535 …
   Stelle: …/smtp_send.py:95 in send   (letzte 8 Zeilen des Tracebacks)
…
Bericht-ID: <zufällig>   Gesendet über das Mailkonto der Installation.
```

Kein Benutzername, keine Mailadresse des Nutzers (außer als Absender, wenn der Admin sie als Absender eingetragen hat),
keine Sitzungs- oder Agenten-ID, keine Pfade unterhalb von `$HOME` (auf `~` gekürzt).

## Sicherheit

- Senden nur über die Route nach Klick – **kein Werkzeug sendet**. Das Modell kann den Bericht vorbereiten, nicht
  abschicken (Schutz gegen eingeschleuste Anweisungen aus Fehlertexten oder Mails).
- Entwurf gehört dem Nutzer (fremde ID → 404), einmal sendbar, läuft nach 30 min ab.
- Höchstens 3 gesendete Berichte je Nutzer und Stunde, 10 je Installation und Stunde.
- Fehlerprotokoll nur des eigenen Nutzers (Admins: auch Einträge ohne Nutzer, z. B. Hintergrundaufgaben).
- Doppelte Schwärzung: `errors_log` schwärzt beim Schreiben, das Werkzeug noch einmal mit den Secrets des Nutzers
  (`redaction.egress_secrets`), wie `send_mail`.
- Empfänger fest (Konstante/Umgebung), nicht vom Modell oder Nutzer wählbar.

## Dateien (Kern, je ≤ 200 Zeilen)

- `core/src/hydrahive/helpdesk/_report.py` – Daten sammeln, Vorlage, Entwürfe im Speicher, Grenzen.
- `core/src/hydrahive/helpdesk/_report_send.py` – Versand über das Mailkonto / mailto-Daten.
- `core/src/hydrahive/tools/error_report_prepare.py` – Werkzeug für den Hilfe-Agenten.
- `core/src/hydrahive/api/routes/helpdesk.py` – `GET /report/{id}`, `POST /report/{id}/send`, `DELETE /report/{id}`.
- `helpdesk/_agent.py` – `HELP_TOOLS` + Werkzeug, Systemprompt-Abschnitt „Fehler melden“.
- `settings/editable.py` – Schalter.
- Frontend `features/helpdesk/`: Karte `HelpReportCard.tsx`, Erkennen des Werkzeug-Ergebnisses im Verlauf, i18n DE/EN.
- Hilfe-Artikel `helpdesk.md` (DE/EN): Abschnitt „Fehler melden“.

## Tests (zuerst rot)

- Nur eigene Fehler im Bericht; fremder Nutzer sieht/sendet den Entwurf nicht (404).
- Secrets (Testwert) erscheinen nie im Bericht, auch nicht im Traceback.
- Mit Mailzugang: genau eine Mail an die feste Adresse über `_transport` (Attrappe), Betreff/Inhalt nach Vorlage.
- Ohne Mailzugang: `mailto`-Daten, kein Versandversuch.
- Schalter aus: Werkzeug und Route lehnen ab.
- Grenzen: 4. Bericht in einer Stunde → 429.
- Werkzeug kann nicht senden (es gibt keinen Pfad dorthin); Entwurf läuft ab.
- Frontend: Karte, Senden, mailto-Knopf + Einrichten-Link (Admin) bzw. Hinweis (Nutzer).

## Offen für Till

1. **Zieladresse** des Fehler-Postfachs.
2. Schalter-Standard **an** (Vorschlag, wegen der externen Nutzer) oder aus.
