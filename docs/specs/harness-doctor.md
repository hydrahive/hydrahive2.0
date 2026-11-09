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

## Oberfläche

Admin-only Reiter `Harness` im Systemfenster: Gesamtscore, Dimensionskarten, priorisierte Maßnahmen, Evidenzliste und Agent-Ausreißer. Zeitraum 24 h / 7 d / 30 d. Keine Reparaturknöpfe.

## Sicherheit und Grenzen

- `require_admin`; keine Mutation, Shell, Netzwerk- oder Provideraufrufe.
- SQL nur aggregiert und zeitlich begrenzt.
- MCP-Remote-Schemas werden nicht geladen; Tool-Schema-Größe bezeichnet lokale registrierte Schemas vor per-User Access-Filter.
- Korrelationen werden nicht als Ursachen ausgegeben.
- Der Doctor ersetzt keine Tests und keine unabhängige Verifikation.
