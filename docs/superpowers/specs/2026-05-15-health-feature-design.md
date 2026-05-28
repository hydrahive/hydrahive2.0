# Health Feature Design

**Datum:** 2026-05-15  
**Status:** Genehmigt

## Überblick

Apple Health Auto Export liefert Gesundheitsdaten per Ingest-API. Dieses Feature macht die Daten für Till sichtbar (Frontend) und für Buddy auswertbar (Tool).

---

## 1. Backend

### Neuer Endpunkt: `GET /api/health-data/metrics`

**Datei:** `core/src/hydrahive/api/routes/health_data.py`

**Parameter:**
- `days` (int, default 7) — Zeitraum in Tagen
- `metric` (str, optional) — Filter auf eine spezifische Metrik

**Verhalten:** Liest alle `health_ingest`-Records des angegebenen Zeitraums, parst die gespeicherten Apple-Health-Payloads on-the-fly, aggregiert Messwerte pro Metrik und Tag.

**Response:**
```json
{
  "metrics": {
    "step_count": {
      "latest": 8432,
      "trend": "+12%",
      "unit": "count",
      "days": [{"date": "2026-05-15", "value": 8432}, ...]
    },
    "heart_rate": {
      "latest": 68,
      "trend": "0%",
      "unit": "bpm",
      "days": [...]
    }
  },
  "last_ingest": "2026-05-15T22:49:00Z",
  "period_days": 7
}
```

**Auth:** Gleiche Key-Validierung wie die bestehenden Endpunkte (`X-HH-Health-Key`, `Authorization: Bearer`, `?key=`).

**Aggregationsregeln pro Metrik-Typ:**
- Kumulative Metriken (step_count, active_energy_burned, basal_energy_burned): **Summe** pro Tag
- Durchschnittswerte (heart_rate, respiratory_rate, blood_oxygen_saturation): **Mittelwert** pro Tag
- Zeitbasierte Metriken (sleep_analysis): **Summe** der Minuten pro Tag
- Unbekannte Metriken: Mittelwert als sicherer Fallback

**Trend-Berechnung:** Letzter Tageswert vs. Durchschnitt der restlichen Tage im Zeitraum.

### Neue DB-Funktion

**Datei:** `core/src/hydrahive/db/health.py`

`get_metrics_summary(days: int, metric: str | None) -> dict` — liest Records des Zeitraums, parst JSON-Payloads, aggregiert nach Metrik-Name. Trend = Vergleich letzter Wert vs. Durchschnitt der Vortage.

---

## 2. Buddy-Tool `query_health_data`

**Datei:** `core/src/hydrahive/tools/health_data.py`

**Schema:**
```json
{
  "metric": "optional — z.B. step_count, heart_rate, sleep_analysis",
  "days": "Zeitraum in Tagen (default 7)"
}
```

**Verhalten:** Ruft intern `GET /api/health-data/metrics` auf. Liest den API-Key aus `settings.health_api_key` — der Key erscheint nie im LLM-Kontext (analog zu `fetch_url`).

**Registrierung:** Tool wird in `core/src/hydrahive/tools/__init__.py` hinzugefügt und steht Buddy zur Verfügung.

---

## 3. Frontend

### Feature-Ordner: `frontend/src/features/health/`

| Datei | Verantwortung |
|-------|---------------|
| `HealthPage.tsx` | Split-View Hauptseite |
| `_MetricCards.tsx` | Obere Karten-Reihe: Schritte, Schlaf, Herzfrequenz, Kalorien mit aktuellem Wert + Trend-Badge |
| `_IngestList.tsx` | Untere Liste der Ingest-Pakete; Klick klappt alle Metriken des Pakets aus |
| `_HealthBuddyBox.tsx` | Kompakte Box für BuddyPage: Status-Indikator, letzter Ingest-Zeitstempel, 3 Analyse-Buttons |
| `api.ts` | API-Client für `/metrics` und `/data` Endpunkte |

### `HealthPage.tsx` — Layout

```
┌─────────────────────────────────────┐
│  🦶 8.432      ❤️ 68     😴 6h45   │  ← _MetricCards (obere Hälfte)
│  Schritte ↑12% HF →0%  Schlaf ↓5% │
├─────────────────────────────────────┤
│  Ingest-Verlauf                     │  ← _IngestList (untere Hälfte)
│  ▶ 15.05.2026 · 11 Metriken        │
│  ▶ 14.05.2026 · 9 Metriken         │
└─────────────────────────────────────┘
```

Keine externe Chart-Library. Trends als Text-Badge (↑ +12%, → 0%, ↓ -5%) und CSS-Mini-Balken.

### `_HealthBuddyBox.tsx` — Buddy-Integration

```
┌─────────────────────────────────────────┐
│ ● Health aktiv · 15.05. 22:49  → /health│
│ [📊 Tagesauswertung] [📈 Wochentrend]   │
│ [😴 Schlafqualität]                     │
└─────────────────────────────────────────┘
```

Die drei Buttons senden einen vorformulierten Prompt in den Buddy-Chat (analog zur bestehenden Cmd-Pill-Logik in `_BuddyCmdPill.tsx`).

### Routing und Navigation

- **App.tsx:** Route `<Route path="health" element={<HealthPage />} />`
- **Sidebar/BentoMenu:** Neuer Eintrag "Gesundheit" mit 🫀-Icon, eingeordnet nach "Dashboard"
- **BuddyPage:** `_HealthBuddyBox` in den linken Panel eingebunden (unterhalb bestehender Extensions-Panel)

### Auth im Frontend

Die Health-Seite nutzt die bestehende Session-Auth (JWT-Cookie). Der `HH_HEALTH_API_KEY` wird **nicht** im Frontend verwendet — Frontend läuft unter demselben Auth-Kontext wie alle anderen Seiten.

---

## 4. Scope-Grenzen

- Kein Chart-Framework (Recharts, Chart.js etc.) — zu groß für den Nutzen
- Keine Echtzeit-Updates (kein WebSocket/SSE für Ingest-Benachrichtigungen)
- Keine Health-Daten in anderen Bereichen außer `/health` und Buddy-Box
- Keine manuelle Dateneingabe — ausschließlich Apple Health Auto Export als Quelle
