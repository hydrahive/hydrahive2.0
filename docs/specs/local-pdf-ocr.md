# Lokales Lesen von Text- und Scan-PDFs

Status: **FREIGEGEBEN** durch Till am 03.11.2026 („ja plane es und setze es um“)

## Problem

Agenten können PDFs im Projekt derzeit nicht zuverlässig lesen. `file_read` behandelt Binärdateien als UTF-8-Text. Auf macOS fehlen zudem Poppler und Tesseract. Text-PDFs bleiben dadurch unlesbar; reine Scan-PDFs enthalten überhaupt keine extrahierbare Textebene.

## Ziel

HydraHive stellt allen Master- und Projektagenten auf Host-Projekten ein Werkzeug `read_document` bereit. Es liest PDF-Dateien ausschließlich lokal:

1. vorhandene Textebene mit Poppler auslesen;
2. Seiten ohne hinreichende Textebene lokal mit Tesseract OCR erkennen;
3. Text direkt als Werkzeugergebnis mit Seitenmarken liefern.

Es werden weder Dokumente noch Seitenbilder an einen Cloud-Dienst übertragen. Eine dauerhafte `.txt`-Kopie oder eine veränderte PDF wird nicht automatisch erzeugt.

## Werkzeugvertrag

Name: `read_document`

Eingaben:

- `path` (Pflicht): relativer oder absoluter Pfad; muss über den bestehenden lesenden Workspace-Pfadschutz erreichbar sein und auf `.pdf` enden.
- `page_start` (optional, Standard 1): erste Seite, 1-basiert.
- `page_limit` (optional, Standard 10, Maximum 20): Anzahl Seiten dieses Aufrufs.
- `ocr_language` (optional, Standard `deu+eng`): Tesseract-Sprachen; nur Buchstaben/Ziffern, `_`, `-` und `+`, maximal 64 Zeichen.
- `force_ocr` (optional, Standard false): OCR auch bei vorhandener Textebene, etwa für fehlerhafte eingebettete Schrift.

Ausgabe:

- Text mit `[Seite N]` vor jeder Seite;
- Metadaten `path`, `total_pages`, `returned_pages`, `text_pages`, `ocr_pages`, `next_page`, `truncated`;
- bei fehlenden Laufzeitprogrammen eine klare lokale Installationsmeldung, keine stillen leeren Ergebnisse.

## Verarbeitungsregeln

1. Pfad mit `read_path()` auflösen (eigener Workspace plus wirksam verknüpfte Projekte); Symlinks werden aufgelöst.
2. Nur reguläre Dateien mit `.pdf`, PDF-Kennung `%PDF-` und höchstens 100 MiB akzeptieren.
3. `pdfinfo` ermittelt die Seitenzahl. Verschlüsselte, beschädigte oder nicht lesbare PDFs liefern einen begrenzten Fehler ohne Dokumentinhalt.
4. `pdftotext -layout` liest den gewählten Seitenbereich in einem Aufruf.
5. Eine Seite gilt als sinnvoll lesbar, wenn sie mindestens 20 alphanumerische Zeichen enthält.
6. Nur fehlende/zu kurze Seiten werden mit `pdftoppm` auf maximal 2500 Pixel Kantenlänge gerendert und mit `tesseract` erkannt. Temporäre Bilder liegen in einem automatisch gelöschten temporären Ordner.
7. Maximal 20 Seiten und 100.000 Ausgabezeichen je Aufruf. Bei Kürzung weist das Ergebnis auf einen kleineren Seitenbereich hin.
8. Die geprüfte PDF wird aus demselben symlink-sicher geöffneten Dateideskriptor in einen privaten Snapshot kopiert; ausschließlich dieser unveränderliche Snapshot erreicht die Parser.
9. Externe Prozesse erhalten nur eine minimale Umgebung ohne Provider-Keys oder HydraHive-Secrets. Pfade werden als einzelne Argumente übergeben, nie in Shell-Text eingesetzt.
10. Parser laufen fail-closed in einer lokalen Sandbox: Linux über Bubblewrap mit eigenem Mount-, PID- und Netzwerk-Namespace je Aufruf; ein geladenes AppArmor-Profil erlaubt Bubblewrap auf restriktiven Ubuntu-Systemen den benötigten User-Namespace. Nur der aktuelle Snapshot ist read-only und nur sein privater Arbeitsordner schreibbar eingebunden. macOS nutzt `sandbox-exec` mit deny-by-default-Profil. Fehlt die Isolation, wird nicht geparst.
11. Jeder Prozess und der gesamte OCR-Lauf besitzen Zeitlimits; beim Abbruch wird die Prozessgruppe beendet. Linux begrenzt zusätzlich Adressraum, CPU, Dateigröße, Prozesse und Deskriptoren über `prlimit`; stdout wird inkrementell hart begrenzt.

## Plattformen

### macOS

Erstinstallation und bestehende Updates stellen bereit:

- `poppler` (`pdfinfo`, `pdftotext`, `pdftoppm`)
- `tesseract`
- `tesseract-lang` (u. a. Deutsch)

Homebrew wird über `mac-roles.sh` als `HH_BREW_USER` ausgeführt. HydraHive selbst bleibt unter `_hydrahive`. Apple Silicon (`/opt/homebrew`) und Intel (`/usr/local`) bleiben unterstützt.

### Ubuntu/Debian

Erstinstallation und bestehende Updates stellen bereit:

- `poppler-utils`
- `tesseract-ocr`
- `tesseract-ocr-deu`
- `tesseract-ocr-eng`
- `bubblewrap` (Mount-/PID-/Netzwerk-Sandbox je Dokument)
- `apparmor` (User-Namespace-Freigabe für Bubblewrap auf restriktiven Ubuntu-Systemen)
- `util-linux` (`prlimit` für harte Ressourcenlimits)

### Projektcontainer

V1 wird nicht an der Container-Allowlist vorbeigeführt. In Projekten mit Ausführung im eigenen Incus-Container ist `read_document` nicht sichtbar, bis ein versioniertes Container-Image dieselben Laufzeitprogramme garantiert. Es gibt keinen unsicheren Rückfall auf den Host.

## Agenten und Bedienung

`read_document` wird ein kanonisches Standardwerkzeug für Master- und Projektagenten. Der bestehende Agent-Bootstrap ergänzt es idempotent bei vorhandenen Agenten. Die Werkzeugbeschreibung weist Agenten an, PDFs hiermit statt mit `file_read` zu lesen.

## Sicherheit und Datenschutz

- keine Netzwerkverbindung im Werkzeug oder in der Parser-Sandbox;
- kein Cloud-OCR;
- kein Zugriff außerhalb zulässiger lesender Projektpfade; Parser sehen nur den privaten Snapshot, Systembibliotheken und einen leeren Arbeitsordner;
- keine Shell-Interpolation von Nutzerpfaden oder Sprachnamen;
- begrenzte Dateigröße, Seitenzahl, Bildgröße, Ausgabe und Laufzeit;
- Kindprozesse erhalten keine API-Keys, Tokens oder Datenbankzugänge;
- temporäre Seitenbilder werden immer gelöscht;
- Fehler enthalten keine Dokumenttexte und keine vollständigen fremden Systempfade über den bereits freigegebenen Anzeigepfad hinaus.

## Akzeptanzkriterien

1. Eine echte Text-PDF liefert lokalen Text mit Seitenmarken ohne OCR.
2. Eine reine Scan-PDF liefert lokalen OCR-Text und markiert die OCR-Seiten.
3. Eine gemischte PDF nutzt OCR nur für Seiten ohne Text.
4. Seitenbereiche und Fortsetzung funktionieren bis zum Dokumentende.
5. Pfad-Traversal, Symlink-Ausbruch, Nicht-PDF, falsche Kennung, übergroße Dateien und ungültige OCR-Sprachen werden abgelehnt.
6. Fehlende Programme, Timeout, verschlüsselte oder beschädigte PDFs liefern verständliche Fehler.
7. Kindprozesse sehen keine HydraHive-/Provider-Secrets.
8. macOS-Neuinstallation und normales Update bestehender Macs installieren fehlende Programme unter der richtigen Homebrew-Rolle.
9. Ubuntu-Neuinstallation und normales Update bestehender Instanzen installieren fehlende Programme.
10. Container-Projekte erhalten das Werkzeug in V1 nicht.

## Nicht Bestandteil

- PDF bearbeiten, signieren oder zusammenführen;
- durchsuchbare PDF-Kopie erzeugen;
- automatische `.txt`-Sidecars;
- Handschrifterkennung;
- Tabellen-/Layoutrekonstruktion über den Textmodus von Poppler/Tesseract hinaus;
- Cloud-OCR oder Versand von Dokumentseiten an ein LLM;
- Installation in frei konfigurierten Projektcontainern.
