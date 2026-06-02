# Feature Map: Zahnfee — Zahngesundheits-Tracking

> **Modul:** `core/src/hydrahive/zahnfee/`  
> **Frontend:** `frontend/src/features/zahnfee/`  
> **Was:** Spezialisiertes Modul zum Tracken von Zahnarztterminen, Befunden und Zahnstatus.  
> **Warum:** Teil der persönlichen Gesundheitsverwaltung — komplementär zur FHIR-Patientenakte.

---

## Konzept

Zahnfee ist ein spezialisiertes Sub-Modul der Gesundheitsverwaltung:
- Eigener Datenspeicher (nicht FHIR — zu spezifisch)
- Zahn-by-Zahn-Status (FDI-Nomenklatur: 11–48)
- Befund-History pro Zahn
- Termin-Erinnerungen (Integration mit Buddy-Agent)
- KI-Analyse: "Welcher Zahn macht am meisten Probleme?"

---

## Zahnschema (FDI)

```
Oberkiefer rechts: 18 17 16 15 14 13 12 11
Oberkiefer links:  21 22 23 24 25 26 27 28
Unterkiefer links: 31 32 33 34 35 36 37 38
Unterkiefer rechts:41 42 43 44 45 46 47 48
```

---

## Datenmodell

```python
class Tooth:
    tooth_id: str          # FDI: "11", "36", etc.
    status: str            # healthy | filling | crown | implant | missing | root_canal
    last_treatment: date
    notes: str

class DentalAppointment:
    date: date
    dentist: str
    type: str              # checkup | treatment | emergency
    findings: list[ToothFinding]
    cost: float
    notes: str

class ToothFinding:
    tooth_id: str
    finding: str           # karies | parodontitis | fraktur | ...
    severity: int          # 1-5
    treatment_done: str    # füllung | wurzelbehandlung | ...
```

---

## API-Endpoints

| Endpoint | Beschreibung |
|---|---|
| `GET /api/zahnfee/teeth` | Alle Zähne mit Status |
| `PUT /api/zahnfee/teeth/{id}` | Zahn-Status aktualisieren |
| `GET /api/zahnfee/appointments` | Termine-Liste |
| `POST /api/zahnfee/appointments` | Termin anlegen |
| `PUT /api/zahnfee/appointments/{id}` | Termin bearbeiten |
| `DELETE /api/zahnfee/appointments/{id}` | Termin löschen |
| `GET /api/zahnfee/summary` | KI-Zusammenfassung des Zahnstatus |

---

## Frontend

| Datei | Verantwortung |
|---|---|
| `zahnfee/ZahnfeePage.tsx` | Haupt-Seite: Zahnschema + Termine |
| `zahnfee/ZahnSchema.tsx` | Interaktives Zahnschema (SVG) |
| `zahnfee/ToothDetail.tsx` | Detail-Panel für einzelnen Zahn |
| `zahnfee/AppointmentList.tsx` | Termin-Liste |
| `zahnfee/AppointmentForm.tsx` | Termin anlegen/bearbeiten |

---

## Integration mit Buddy

Buddy-Agent kann:
- Zahnfee-Daten über `query_fhir_data` (oder eigenes Tool) abfragen
- Termin-Erinnerungen generieren
- KI-Analyse durchführen: "Wann war mein letzter Check-up?"

---

## Verwandte Subsysteme

- **→ Patientenakte** (`18-patientenakte.md`): FHIR für andere Gesundheitsdaten
- **→ Buddy** (`09-buddy.md`): Termin-Erinnerungen via Buddy
