---
name: document-reading
description: PDFs lokal lesen — Text-PDFs direkt, Scan-PDFs automatisch per OCR; Seitenbereiche, Datenschutz und typische Fehler.
when_to_use: Wenn der User eine PDF lesen, auswerten, zusammenfassen oder Text aus einem eingescannten Dokument erkennen lassen möchte.
tools_required: [read_document]
---

# PDF-Dokumente lokal lesen

Nutze für PDF-Dateien immer `read_document`, nicht `file_read`. Das Werkzeug arbeitet vollständig lokal: Vorhandener PDF-Text wird direkt ausgelesen, Seiten ohne brauchbare Textebene werden automatisch per OCR erkannt. Dokumente und Seitenbilder werden nicht an einen Cloud-Dienst gesendet.

## Ablauf

1. `read_document(path=...)` aufrufen.
2. Bei langen Dokumenten zunächst die ersten Seiten lesen. Das Ergebnis nennt `next_page`, wenn weitere Seiten vorhanden sind.
3. Mit `page_start=next_page` weiterlesen; `page_limit` bei Bedarf verkleinern.
4. Nur wenn eingebetteter PDF-Text sichtbar falsch ist, denselben Bereich mit `force_ocr=true` erneut lesen.
5. Erkennt das Werkzeug eine Sprache schlecht, `ocr_language` passend setzen, z. B. `deu`, `eng` oder `deu+eng`.

## Grenzen und Fehler

- Das Werkzeug liest nur PDFs innerhalb des eigenen oder eines wirksam verknüpften Projekt-Workspace.
- Handschrift und komplexe Tabellen können ungenau sein. Unsichere Werte nicht als sicher darstellen.
- „Dokument-Werkzeuge fehlen“ bedeutet, dass Poppler oder Tesseract auf der Installation fehlen. Nicht über eine Cloud ausweichen und nicht selbst beliebige Programme herunterladen; den Nutzer auf das HydraHive-Update hinweisen.
- Verschlüsselte PDFs benötigen zuerst eine vom Nutzer bereitgestellte entschlüsselte Kopie. Nicht nach einem Passwort fragen, wenn das Dokument auch lokal vom Nutzer entschlüsselt werden kann.
- Automatisch erkannte medizinische, rechtliche oder finanzielle Angaben als OCR kennzeichnen und wichtige Werte anhand der sichtbaren Vorlage verifizieren lassen.
