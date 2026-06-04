---
name: medical-akte
description: Strukturierte Patientenakte (ePA-light) über die REST-API befüllen — Diagnosen, Medikamente, Laborwerte, Ereignisse, Bildgebung, Dokumente.
when_to_use: Wenn du aus Dokumenten/Daten extrahierte medizinische Informationen in die Patientenakte schreiben oder abfragen sollst (z. B. nach OCR eines Arztbriefs/Laborbefunds).
tools_required: [fetch_url]
metadata:
  category: health
---

# Patientenakte befüllen

Du schreibst strukturierte medizinische Daten über die REST-API in die Patientenakte.
Aufrufe per `fetch_url` gegen die lokale HydraHive-API. Die Patientenakte ist ein
installiertes Modul (`patientenakte`) — die Endpunkte liegen daher unter
`/api/modules/patientenakte/akte`.

- **Basis:** `http://127.0.0.1:8000/api/modules/patientenakte/akte` (Port ggf. anpassen)
- **Auth:** `Authorization: Bearer <hhk_…>` (API-Key des Nutzers mit Akte-Zugriff)
- **Body:** JSON. Immer `Content-Type: application/json` setzen.
- **Single-User:** Jeder Nutzer hat genau EINE Akte (kein `pid` im Pfad). Der Key
  bindet an den Nutzer; Einträge gehen direkt in dessen Akte.

## Grundregeln

1. **Erst die eigene Akte holen** (`GET /`) — gibt 404 wenn noch keine existiert; dann
   einmalig **anlegen** (`POST /`). Danach Einträge direkt schreiben.
2. **Idempotenz:** Gib bei jedem Eintrag eine stabile `external_id` mit (z. B.
   `<quelle>-<datum>-<code>`). Ein erneuter POST mit gleicher `external_id` aktualisiert
   den Eintrag, legt kein Duplikat an.
3. **Herkunft kennzeichnen:** `quelle` (woher), `confidence` (0..1), `verifiziert` (false
   bei automatischer Extraktion). Nicht raten — `confidence` ehrlich setzen.
4. **Laborwerte als Batch** schicken (viele Parameter, ein Datum).

## Eigene Akte (Stammdaten)

```
GET    /                       # eigene Akte inkl. counts je Entität (404 = noch keine)
POST   /                       # einmalig anlegen {slug, name, vorname, geburtsdatum,
                               #  geschlecht, adresse{...}, versicherung{...}, notfallkontakt{...}}
PATCH  /                       # Stammdaten aktualisieren
```

## Einträge (generisch je {entity})

`{entity}` ∈ `conditions` (Diagnosen) · `medications` · `observations` (Labor) ·
`events` (Ereignisse/OP) · `imaging` (Bildgebung) · `allergies` · `practitioners` (Ärzte) ·
`documents` · `notes`

```
GET    /{entity}                 # Liste (+?q=, +?status=)
POST   /{entity}                 # anlegen / per external_id upserten
POST   /{entity}/batch           # {items:[...]} — v.a. observations
GET    /{entity}/{id}
PATCH  /{entity}/{id}
DELETE /{entity}/{id}
GET    /timeline                 # chronologisch über alle Entitäten
GET    /summary                  # Zähler je Entität
```

### Felder je Entität
- **conditions:** diagnose, icd_code, status, diagnostiziert_am, arzt, koerperstelle, erstmanifestation, bemerkungen
- **medications:** name, wirkstoff, atc_code, klasse, dosierung, beginn, ende, arzt, zweck, status (`aktuell`/`historisch`), letzte_verordnung, nebenwirkungen[]
- **observations:** parameter, wert (Zahl), wert_text, einheit, referenz_min, referenz_max, flag, datum, labor, material
- **events:** datum_von, datum_bis, typ, einrichtung, fachabteilung, fallnummer, hauptdiagnose, verlauf, nebendiagnosen[], prozeduren[], op_codes[], entlassmedikation[]
- **imaging:** datum, modalitaet, region, einrichtung, ueberweiser, serien_beschreibung, anzahl_bilder, dicom_pfad, befund, vorschau_bilder[]
- **allergies:** substanz, reaktion, schweregrad, festgestellt_am
- **practitioners:** name, fach, einrichtung, adresse, telefon, rolle (`hausarzt`/`facharzt`/`sonstige`)
- **documents:** titel, typ, datum, datei_pfad, mime_type, ocr_text
- **notes:** titel, inhalt (Markdown), kategorie, datum

Alle Entitäten akzeptieren zusätzlich: `external_id`, `quelle`, `confidence`, `verifiziert`.

## Beispiele

Diagnose anlegen (aus Arztbrief-OCR):
```
fetch_url(
  "http://127.0.0.1:8000/api/modules/patientenakte/akte/conditions",
  method="POST",
  headers={"Authorization": "Bearer <hhk_…>", "Content-Type": "application/json"},
  body='{"external_id":"kath-2024-11-K75.0","diagnose":"Leberabszess","icd_code":"K75.0",'
       '"status":"behandelt","diagnostiziert_am":"2024-11-21","arzt":"Dr. Morlang",'
       '"quelle":"Arztbrief OCR mediscan.pdf","confidence":0.9,"verifiziert":false}',
)
```

Laborwerte als Batch (eine Tabelle, ein Datum):
```
fetch_url(
  "http://127.0.0.1:8000/api/modules/patientenakte/akte/observations/batch",
  method="POST",
  headers={"Authorization": "Bearer <hhk_…>", "Content-Type": "application/json"},
  body='{"items":['
       '{"external_id":"lab-2025-03-01-hba1c","parameter":"HbA1c","wert":7.8,"einheit":"%","datum":"2025-03-01"},'
       '{"external_id":"lab-2025-03-01-egfr","parameter":"eGFR","wert":93,"einheit":"ml/min","datum":"2025-03-01"}'
       ']}',
)
```
