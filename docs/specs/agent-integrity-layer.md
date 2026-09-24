# Agent Integrity Layer

## Ziel

HydraHive-Agenten sollen nicht nur technisch begrenzt, sondern auch gegen semantische Fehlentwicklungen geschützt werden: Endlosschleifen mit wechselnden Parametern, Drift vom Auftrag, unbelegte Wirkungsbehauptungen, verlorene Herkunft und riskantes Weiterarbeiten nach fehlgeschlagenen Eingriffen.

Die Schutzlogik wird vorrangig im Runner, Tool-Dispatcher und Memory-Modell gebaut. Der Systemprompt bleibt klein, deterministisch und cache-stabil.

## Leitplanken

- Keine turn-dynamischen Integrity-Zustände im `stable_system`-Prompt.
- Keine LLM-Judge-Schleife als Pflichtbestandteil jedes Turns.
- Keine automatische Blockierung allein wegen eines schwachen Signals.
- Jede aktive Schutzentscheidung muss auditierbar und erklärbar sein.
- Bestehende Tool-Rechte, Bestätigungen, Redaction, Session-Guard und Compaction bleiben unverändert.
- Der statische Prompt-Anteil der Integrity Layer erhält ein Budget von höchstens 100 Tokens; Phase 1 kommt ohne zusätzlichen Prompttext aus.

## Signale

### Loop und fehlender Fortschritt

Der Runner erfasst pro Iteration:

- kanonische Tool-Signatur (Toolname plus normalisierte Argumente),
- Ergebnisstatus (Erfolg, Fehler, Ablehnung),
- Ergebnis-Fingerprint ohne Secret-Werte,
- ob seit dem letzten Turn neue Evidenz oder ein neuer Zustand entstanden ist.

Exakte Wiederholungen bleiben der harte Sofortschutz. Zusätzlich werden semantisch gleiche Tool-Aktionen mit variierenden flüchtigen Feldern und wiederholte Fehlerketten als Warnsignal erfasst.

### Provenienz und Evidenz

Tool-Ergebnisse werden als beobachtete Evidenz getrennt von Assistant-Text und Annahmen geführt. Die Layer unterscheidet mindestens:

- `observed` — Tool-/Systemergebnis,
- `claimed` — Aussage ohne passenden Nachweis,
- `derived` — nachvollziehbare Ableitung aus Evidenz,
- `user_decision` — vom Benutzer festgelegte Wahrheit oder Grenze.

### Reality Gate

In Phase 1 werden Wirkungsbehauptungen wie „getestet“, „deployt“, „behoben“ nur erkannt und telemetriert. Eine aktive Sperre wird erst nach Messung der Fehl- und Trefferquote eingeschaltet. Für spätere Enforcement-Phasen müssen erfolgreiche Tool-Nachweise zum behaupteten Wirkungsniveau passen.

Der Evidenzabgleich ist konservativ und promptfrei:

- erfolgreiche Datei-/Skill-Änderungen liefern `artifact_changed`,
- erfolgreiche, nicht maskierte Testkommandos liefern `tests_passed`,
- fehlgeschlagene, gepipte, mit `|| true` maskierte oder reine Collect/Help-Kommandos liefern keine Testevidenz,
- `implemented` benötigt Änderungs- oder Commit-Evidenz,
- `tested` benötigt bestandene Testevidenz,
- `fixed` benötigt Änderung plus bestandenen Test.

Fehlende Evidenz erzeugt zunächst ausschließlich `unverified_completion_claim` im Audit. Rohbefehle, Tool-Ausgaben und Nutzertext werden nicht in das Ledger übernommen.

### Beobachtungsmetriken

Admins können die Beobachtung über `GET /api/system/integrity/summary?hours=24` aggregiert auswerten. Der Endpunkt akzeptiert 1–720 Stunden, liest ausschließlich Message-Metadaten und begrenzt die Verarbeitung auf 10.000 Kandidaten. Die Antwort enthält nur Zähler, Zeitfenster, Truncation-/Malformed-Hinweise und die Quote unbelegter Claims; Nachrichteninhalte sowie User-, Agent- und Session-IDs werden weder selektiert noch zurückgegeben.

Kumulative Evidenz-Snapshots werden je Session als Delta gezählt, damit dieselbe Evidenz nicht in jeder Folgemessage erneut als Ereignis erscheint. Diese Metriken steuern noch kein Enforcement, sondern dienen ausschließlich der Schwellenwert- und Fehlalarmbewertung für Phase 2.

Signale können zusätzlich ein strukturiertes `subject` tragen. Für Claims ist dies ausschließlich die feste Claim-Art (`implemented`, `tested`, `fixed` usw.), für Toolsignale der auf 80 sichere Zeichen begrenzte Toolname. Ungültige Werte, unbekannte Signal-/Evidenzarten und Subjects oberhalb von 100 Kategorien pro Signalart werden als `other` zusammengefasst. Der Admin-Endpunkt aggregiert daraus `claim_counts`, `unverified_claim_counts` und `signal_subject_counts`; alte Signale ohne Subject bleiben gültig. Argumente, Ausgaben, Texte und Identifikatoren sind als Subjects ausgeschlossen.

### Drift und Kontext

Der Runner hält einen kompakten Ziel-/Fortschrittszustand außerhalb des Stable-Prompts. Zunächst werden nur Signale gesammelt: fehlende Zielreferenz, wiederholte Nebenpfade, wechselnde Arbeitsobjekte und fehlender Fortschritt. Ein Stop darf erst aus mehreren Signalen oder einem harten Sicherheitsereignis entstehen.

### Grenzen und Strategie

Schutzentscheidungen verwenden abgestufte Reaktionen:

1. `observe` — nur Telemetrie,
2. `warn` — sichtbarer Hinweis für den nächsten Turn,
3. `dampen` — Umfang/Tool-Freiheit reduzieren,
4. `confirm` — Benutzerbestätigung verlangen,
5. `pause` — Session sauber pausieren,
6. `stop` — nur bei hartem oder wiederholtem Verstoß.

## Phasen

### Phase 1: Beobachtungsmodus

- Integrity-State im Runner.
- Kanonische Tool-/Ergebnis-Fingerprints.
- Fortschritts- und Fehlerketten-Signale.
- Completion-Claim- und Provenienz-Telemetrie.
- Keine zusätzliche dynamische Promptlast.
- Keine neue harte Blockierung außer bereits vorhandenem Loop-/Limit-Schutz.

### Phase 2: Niedrigrisiko-Enforcement

- semantische Wiederholung nach Schwellenwert pausieren,
- wiederholte identische Fehler mit Strategiehinweis beenden,
- Completion-Claims ohne Nachweis als unbestätigt markieren,
- Resume mit sichtbarem Integrity-Zustand starten.

### Phase 3: Wirkungs- und Risiko-Gates

- Nachweisprüfung für Tests, Commits, Push und Deployment.
- Risiko-/Reversibilitätsprüfung vor Änderungen.
- Bestätigung oder FixOnly-/Minimalpatch-Strategie.
- Rollback-/Checkpoint-Hinweise.

### Phase 4: Memory-Integrität

- Quellen und Vertrauenswerte persistieren.
- bestätigte Nutzerentscheidungen schützen,
- widersprochene und veraltete Karten superseden,
- unbelegte Claims nicht als gleichwertigen Recall verwenden.

## Cache-Vertrag

`system_prompt.compose()` behält die stable/volatile/summary-Trennung. Der Stable-Block darf sich nicht pro Turn ändern. Dynamische Integrity-Zustände gehören in Runner-State, Tool-Metadaten oder den separaten Summary-/Volatile-Pfad.

Regressionstests prüfen:

- Stable-Prompt enthält keine Uhrzeit oder Turn-State.
- Stable-Prompt bleibt bei identischer Agent-/Workspace-Konfiguration bytegleich.
- Integrity-Erfassung erhöht den Stable-Prompt nicht in Phase 1.
- Promptgröße und Cache-Read-/Write-Verhältnis werden vor und nach jeder Phase gemessen.

## Akzeptanzkriterien

- [x] Phase 1 erfasst kanonisch äquivalente Tool-Wiederholungen, ohne Rohdaten oder Secrets in Integrity-Metadaten zu persistieren.
- [x] Fehlerketten und fehlender Fortschritt sind pro Session in Message-Metadaten nachvollziehbar.
- [x] Beobachtung ist standardmäßig aktiv, Enforcement zunächst nicht.
- [x] Stable-Prompt bleibt ohne zusätzliche dynamische Integrity-Daten cache-stabil.
- [x] Completion-Claims können von beobachteten Tool-Ergebnissen unterschieden werden.
- [ ] Phase 2: Jede aktive Entscheidung enthält Signal, Schwellenwert und Reaktion im Audit.
- [x] Bestehende Runner-, Tool-, Compaction- und Cache-Tests bleiben grün.

## Nicht in diesem Umfang

- Kein allgemeiner Wahrheitsbeweis für freie Sprache.
- Kein zweiter LLM-Call für jede Antwort.
- Keine automatische Änderung an Dateien, Deployments oder Tickets.
- Keine Änderung des bestehenden Tool-Rechte- oder Secret-Modells.
