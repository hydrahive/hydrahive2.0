# Harness Doctor V1

## Zweck

Ein rein lesender, deterministischer Admin-Audit bewertet HydraHive anhand der fünf Harness-Dimensionen Instructions, Tools/Environment, State, Verification und Scope/Lifecycle. Er verwendet ausschließlich lokale Konfiguration und aggregierte Telemetrie. Jede Wertung nennt Regel, Istwert, Zielwert, Abzug und Datenquelle.

## API

`GET /api/system/harness-doctor?hours=168` — nur Admin, `hours` 1–720.

Antwort: Zeitpunkt, Fenster, Gesamtscore 0–100, niedrigste Dimension, fünf Dimensionsscores mit Evidenz/Funden, zwei bis drei priorisierte Verbesserungen sowie kompakte Agent-Ausreißer. Keine Nachrichteninhalte, Toolargumente, Toolresultate, Secrets oder personenbezogene Detaildaten.

## Regeln V1

- Instructions: Tool-Schema-/Skill-Metadaten-/Systemprompt-Größe und breite Toolkonfiguration.
- Tools/Environment: Host-Shell-Exposition, Confirmation-Konfiguration, Tool-Trunkierungs- und Fehlerrate.
- State: Compaction-Fehlerrate/-p90, Memory-Abdeckung komplexer Agenten, strukturierte Task-Evidenz.
- Verification: Integrity-Unverified-Rate und vorhandene CI-Workflows. (Ein Observe/Enforce-Modus existiert nicht; die ursprüngliche Regel dazu wurde im Review 09.11.2026 entfernt.)
- Scope/Lifecycle: Projekt-Agent-Zuordnung und terminale Delegationsfehler.

Jede Dimension startet bei 100. Nur dokumentierte Regeln ziehen Punkte ab; Minimum 0. Gesamtscore ist der gerundete Mittelwert. Schwellen und Abzüge sind festgelegte Annahmen: Der Score taugt zum Vergleich über die Zeit, nicht als absolute Qualitätsnote. Prioritäten sind die drei höchsten Abzüge, maximal eine pro Regel.

Tool-Fehlerrate: Nur `status = 'error'` zählt als Fehler. `pending` (unbeendet: Aufruf läuft noch oder wurde bei einem Dienstneustart abgebrochen) und `cancelled` (vom Nutzer gestoppt) werden getrennt als `tool_interrupted` und `tool_cancelled` ausgewiesen. Bis 09.11.2026 zählte alles außer `success`, dadurch war die Rate leicht überhöht.

## Häufigste Fehlerursachen

Feld `error_causes` (Task 2123ef7e, Kurs L01/L11): Gesamtzahlen (`errors_total`, `interrupted`, `cancelled`) und die zehn häufigsten Ursachen als `{tool, cause, count, share}`. Zweck: Harness-Lücken wie das fehlende Timeout-Maximum bei `shell_exec` regelmäßig sichtbar machen.

Eine Ursache ist die normalisierte erste Zeile der Fehlermeldung, höchstens 140 Zeichen. Maskiert bzw. entfernt werden:

- Pfade → `<pfad>`, URLs → `<url>`, UUIDs und Hex-IDs → `<id>`, Zahlen → `<n>`, Listen → `[…]`
- Freitext aus Spezialisten-Ausgaben (`Specialist-Status …: Pausiert: …`) und rohes Provider-JSON ab `{`

Kurze Wortpaare wie `speech/tts` bleiben lesbar. Der Probelauf mit den echten Daten der letzten 30 Tage ergab 51 Gruppen ohne Pfad- oder Inhaltsreste.

## Oberfläche

Admin-only Reiter `Harness` im Systemfenster: Gesamtscore, Dimensionskarten, priorisierte Maßnahmen, Evidenzliste, häufigste Fehlerursachen und Agent-Ausreißer. Zeitraum 24 h / 7 d / 30 d. Keine Reparaturknöpfe.

## Sicherheit und Grenzen

- `require_admin`; keine Mutation, Shell, Netzwerk- oder Provideraufrufe.
- SQL nur aggregiert und zeitlich begrenzt (auch die Fehlerursachen: vorgruppiert nach Werkzeug, Status und Meldung).
- MCP-Remote-Schemas werden nicht geladen; Tool-Schema-Größe bezeichnet lokale registrierte Schemas vor per-User Access-Filter.
- Korrelationen werden nicht als Ursachen ausgegeben.
- Der Doctor ersetzt keine Tests und keine unabhängige Verifikation.
