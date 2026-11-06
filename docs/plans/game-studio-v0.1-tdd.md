# Plan: Game Studio V0.1 — atomare TDD-Implementierung

## Status und Voraussetzungen

**Status:** Implementierungsplan nach fachlicher Freigabe der Spezifikation `docs/specs/game-studio-module-v0.1.md`.

Vor Produktivcode gelten diese bereits beschlossenen Grenzen:

- V0.1 enthält keine freie Shell, keine Host-Ausführung und keinen Fallback bei fehlender Isolation.
- Die Compute-Erweiterungen für projektgebundene Jobs und Artefaktuploads sind eine eigene Core-Vorarbeit.
- Godot wird nach einem Linux-MicroVM-Nachweis vollständig unterstützt.
- Unreal bleibt in V0.1 `inventory_only`; ausführende Unreal-Jobs sind nicht Teil dieses Plans.
- Jeder Produktivschritt folgt RED → GREEN → Refactor → gezielter Commit.

## Ziel

Nach Abschluss existiert ein installierbares `game-studio`-Modul. Berechtigte Nutzende können ein neues Spielprojekt anlegen, ein bestehendes Godot-Projekt oder Archiv sicher inventarisieren, Brief und Planung bearbeiten, an einen unveränderlichen Git-Quellstand gebundene Godot-Jobs über einen Linux-MicroVM-Runner starten und deren Phasen, Evidenz sowie sicher angenommene Artefakte im Cockpit sehen.

## Nicht Teil dieses Plans

- ausführende Unreal-Jobs, Windows-VM-Runner oder Unreal-Package;
- eingebauter Code-, Level-, Blueprint-, Material- oder Asset-Editor;
- freie Befehlszeilen, frei formulierbare Tests oder frei wählbare Hostpfade;
- automatische Engine-Upgrades, Migrationen oder Portierungen;
- Store-Release, Multiplayer- oder Telemetrieadapter.

## Reihenfolge und Abhängigkeiten

```text
PR 0  Linux-MicroVM-Nachweis
PR 1  Projektgebundene Core-Game-Ressource
PR 2  Signiertes Game-Job-Protokoll
PR 3  Sichere Artefakt-Upload-Sitzungen
PR 4  Linux-Runner und Godot-Referenzprojekt
PR 5  Game-Studio-Modul: Schema und Zugriffsgrenzen
PR 6  Game-Studio-Modul: Projekte, Dokumente und Inventarfluss
PR 7  Game-Studio-Modul: Runs, Artefakte und Aktivitäten
PR 8  Game-Studio-Frontend: Übersicht, drei Einstiege und Guided Flow
PR 9  Game-Studio-Frontend: Werkbank, responsive UX und Accessibility
PR 10 Agenten-/Skillpaket und Provenienz
PR 11 Ende-zu-Ende-Abnahme
```

PR 1–3 sind die separat reviewbaren Core-Vorarbeiten. PR 4 darf erst nach deren Freigabe beginnen. PR 5–10 setzen PR 1–4 voraus. PR 11 setzt alle vorherigen PRs voraus.

---

## PR 0 — Linux-MicroVM-Nachweis für Godot

**Ziel:** Die zulässige Ausführungsgrenze praktisch nachweisen, bevor ein Game-Studio-Jobmodell produktiv gebaut wird.

### Dateien

- `docs/specs/game-studio-module-v0.1.md` — Referenz auf den freigegebenen Nachweis ergänzen.
- `docs/audit/game-studio-linux-microvm-proof.md` — reproduzierbarer Nachweis mit Toolchain-Versionen, Isolation, Limits und Testergebnissen.
- `node-agent/tests/test_game_runtime_microvm_smoke.py` — explizit aktivierbarer Integrationstest, der eine frische Linux-MicroVM über eine in PR 0 anzulegende, fail-closed Node-Testfixture startet; ohne KVM-/VM-Zugriff wird der Nachweis nicht als bestanden gewertet.

### TDD-Aufgaben

1. **RED:** Test schreiben, der KVM und eine frische Incus-VM mit eigenem Gastkernel verlangt; fehlende Capability, Shared-Kernel-Container und Hostfallback müssen hart scheitern.
2. **GREEN:** Bestehenden Node-Incus-VM-Adapter so ausführen, dass Typ, Gastkernel, Hypervisor-/Image-/Policy-Digests und frischer Lifecycle bestätigt sind.
3. **RED:** Gast-Gegenproben für Netzwerk/Routen/DNS/Metadaten, Host-/Home-/Credential-Mounts, Docker-/Incus-Sockets, Hostgeräte und Umgebungsvariablen schreiben; echte Cross-Project-Autorisierung folgt in PR 1/4.
4. **GREEN:** Nur Loopback im Gast, feste Environment-Positivliste sowie ausschließlich erlaubte VM-Geräte/Mounts nachweisen.
5. **RED:** Harte CPU/RAM/Disk/Inode/PID/Dateianzahl/Laufzeit/Outputgrenzen und separate Cancel-/Timeout-Fälle mit Kindprozess verlangen.
6. **GREEN:** Begrenzte Gast-Outputfläche und VM-Teardown-Primitiv ausführen; Cancel und Timeout müssen VM und Prozessbaum innerhalb der dokumentierten Frist beseitigen.
7. **Nachweis:** Ein minimales, versioniertes Godot-Referenzprojekt ausschließlich in der VM inventarisieren, validieren, exportieren, als Export starten und eine echte Viewport-PNG erfassen.
8. **Audit:** Kein Skip, Mock oder Unit-Test gilt als positiver Nachweis; Bericht pinnt Host/Incus/QEMU, Gastimage-Fingerprint, Gastkernel, Godot, Policy-Digest und Artefakthashes.
9. **Commit:** `test(node): prove isolated game microvm baseline` und `docs(game-studio): record godot linux microvm proof`.

### Abnahmekriterien

- [x] Kein nicht vertrauenswürdiger Projekt- oder Godot-Prozess läuft direkt auf dem Host; dort laufen nur Incus und Hypervisor.
- [x] Eigener Gastkernel ist belegt; Container-, Mock-, Skip- und Hostfallback werden nicht als Nachweis akzeptiert.
- [x] Kein externes Netzwerk, keine Route/DNS/Metadatenverbindung, keine Hostgeräte, Hostmounts, Host-Sockets oder Host-Secrets sind verfügbar.
- [x] Environment ist positiv gelistet; CPU, RAM, Disk, Inodes, PIDs, Dateianzahl, Laufzeit und Output sind hart begrenzt.
- [x] Cancel und Timeout beenden VM und Kindprozesse innerhalb der festgelegten Frist.
- [x] Das exportierte Referenzprojekt startet in der VM und liefert gehashte Screenshot-Evidenz.
- [x] Audit enthält reproduzierbare Versionen, Image-/Kernel-/Policy-Digests und Artefakthashes.

---

## PR 1 — Projektgebundene Core-Game-Ressource

**Ziel:** Eine serverseitig autorisierte Bindung zwischen Core-Projekt, Node und opaque Workstation-Workspace schaffen.

### Dateien

- `core/src/hydrahive/db/migrations/057_compute_game_workspaces.sql` — additive Tabelle `compute_game_workspaces`; `056` ist auf der aktuellen Basis bereits durch den Sessionlisten-Index belegt.
- `core/src/hydrahive/compute/game_resources.py` — Ressourcenmodell, Bindungsprüfung, Generationen und administrative Isolation-Freigaben.
- `core/src/hydrahive/compute/models.py` — typisierte Core-Modelle.
- `core/src/hydrahive/api/routes/compute_game_resources.py` — eigener Router für rollenautorisierte Binding-, Freigabe- und Leserouten; der bestehende Jobrouter bleibt bis PR 2 unverändert.
- `core/tests/test_compute_game_resources.py` — Migration, Persistenz, Generationen, Pfadvalidierung und Freigabewiderruf.
- `core/tests/test_compute_game_resources_api.py` — Projektrollen-, System-Admin- und Cross-Project-Grenzen.

### TDD-Aufgaben

1. **RED:** Migrationstest für eine Game-Resource mit `project_id`, `node_id`, opaque `workspace_handle`, `workspace_generation`, Engineprofil und Referenz auf eine administrative Isolation-Freigabe.
2. **GREEN:** Additive Ressourcen- und Freigabetabellen implementieren; absolute Pfade und Secrets dürfen kein Feld sein.
3. **RED:** Freigabematrix für `node_id + isolation_profile_id + runner_version + policy_digest + proof_digest`: selbst gemeldet, unbekannt, verändert, widerrufen oder ohne Adminbestätigung muss scheitern.
4. **GREEN:** Auditierte Freigabe mit `approved_by/at`, Widerruf und exakter Bindungsprüfung implementieren; keine automatische Übernahme aus NodeCapabilities.
5. **RED:** Eine über die Benutzer-API angelegte Bindung bleibt `pending`; ein frei eingesandter opaque Handle darf niemals als lokal bestätigt oder ausführbar gelten.
6. **GREEN:** Ressourcenanlage und zentrale Ausführungsvalidierung fail-closed implementieren; die authentifizierte lokale Handle-Bestätigung und deren Jobintegration folgen mit dem Workstation-/Jobvertrag.
7. **RED:** Parametrisierte Rollenmatrix nach bestehendem Core-Vertrag: Nichtmitglied und zu schwache Rolle erhalten 403 `project_no_access`, `read` darf lesen, Projekt-`admin` darf binden/rotieren; Isolation-Freigaben bleiben System-Admin-only.
8. **GREEN:** Einzigen Core-Projektguard und separaten System-Admin-Guard für alle Routen verwenden.
9. **RED:** Cross-Project-, Node-, Generation-, Freigabe-, Node-Revoke- und gelöschte-Projekt-Konflikte testen.
10. **GREEN:** Fail-closed-Validierung und Orphan-/Revoke-Verhalten implementieren.
9. **Commit:** `feat(compute): add project-bound game workspace resources`.

### Abnahmekriterien

- [x] Keine Workspace-Ressource kann projektübergreifend gelesen oder geändert werden.
- [x] Nur opaque Handles werden gespeichert/ausgegeben.
- [x] Generationwechsel invalidiert alte Bindungen.
- [x] Die zentrale Ausführungsvalidierung lehnt jede nicht exakt passende, aktive und auditierte Isolation-Freigabe ab; Queue, Lease und Start werden in PR 2 verpflichtend daran angebunden.

---

## PR 2 — Signiertes, typisiertes Game-Job-Protokoll

**Ziel:** `game-runtime/v1` als festes, schema-strenges Compute-Protokoll ergänzen.

### Dateien

- `core/src/hydrahive/db/migrations/058_compute_game_jobs.sql` — persistente Projekt-, Provider-, Game-Ressourcen-, Generation- und Quellstandsbindungen für Core-Jobs; erweitert bestehende Constraints additiv.
- `core/src/hydrahive/compute/models.py` — Game-Job-Envelope und Operationstypen.
- `core/src/hydrahive/compute/jobs.py` — Signierung, Lease, Projekt-/Ressourcenbindung und Cancel.
- `core/src/hydrahive/compute/job_protocol.py` — kanonischer signierter Envelope und authentifizierte Cancel-Control-Plane.
- `core/src/hydrahive/compute/providers/game_runtime_v1.py` — Providerregistrierung und Payload-Validierung.
- `core/src/hydrahive/api/routes/compute_game_jobs.py` — getrennte projektrollenbasierte Start-/Status-/Cancel-Routen; die bestehende eigentümerbasierte Legacy-Job-API bleibt rückwärtskompatibel.
- `node-agent/src/hydrahive_node/jobs.py` — Annahme und Weiterleitung ausschließlich gültiger Game-Jobs.
- `node-agent/src/hydrahive_node/runtime.py` und `job_runtime.py` — Providerdispatch, Cancel-Signal, Frist und terminale Bestätigung.
- `core/tests/test_compute_game_jobs.py` und `node-agent/tests/test_game_job_protocol.py` — Master-, Persistenz-, Dispatch- und Cancel-Vertrag.

### TDD-Aufgaben

1. **RED:** Migrationstest: `game_workspace`, `project_id`, Provider-, Game-Ressourcen-, Generation- und Quellstandsbindungen müssen persistierbar sein; bestehende Container-/VM-/Node-Jobs bleiben gültig.
2. **GREEN:** Additive Jobmigration und rückwärtskompatible Modelle implementieren; Core-Jobs behalten den Automaten ab `queued`, fachliches `created` bleibt Modul-Run-Zustand.
3. **RED:** Testfälle für jede erlaubte Operation ausführen: `inspect`, `inventory`, `validate`, `build`, `test`, `run_observe`, `export`.
4. **GREEN:** String-Literale durch geschlossene Typen/Enums und versionierte Payload-Schemas ersetzen.
5. **RED:** Unbekannte Payload-Felder, Shell, Hostpfade, Umgebungsvariablen, Mounts und Secrets müssen abgelehnt werden.
6. **GREEN:** Strict-Schema-Decoder auf Master und Node implementieren.
7. **RED:** Signatur-, Provider-, Node-, Projekt-, Resource-, Generation-, Freigabe-, Lease-, Snapshot- und Source-Commit-Mismatch testen.
8. **GREEN:** Jede Bindung vor Queue, Lease und unmittelbar vor Start prüfen.
9. **RED:** `read` darf Status lesen, `write` starten, `admin` bindungsbezogen verwalten; Cancel nur mit korrekter Projektrolle.
10. **GREEN:** Projektrollen statt bisheriger `created_by`-Sicht für Game-Jobs durchsetzen.
11. **RED:** REST-Cancel muss als persistente Control-Plane-Anforderung den authentifizierten Node innerhalb einer festen Frist erreichen, den aktiven Game-Handler abbrechen und terminal bestätigen; Reconnect darf den abgebrochenen Versuch nicht neu starten.
12. **GREEN:** Cancel-Anforderung, Node-Control-Polling, Handler-Abbruch und persistente terminale Bestätigung implementieren. Das konkrete VM-/Gastprozessbaum-Teardown wird mit dem echten Game-Runtime-Adapter in PR 4 belegt.
13. **Commit:** `feat(compute): add signed game runtime job protocol`.

### Abnahmekriterien

- [x] Keine freie Kommandozeile kann in einen Game-Job gelangen.
- [x] Alle unbekannten Felder führen zu `job_rejected`.
- [x] Jobzugriffe folgen ausschließlich Projektrollen.
- [x] Cancel erreicht einen laufenden Node innerhalb der festgelegten Frist, bricht den aktiven Handler ab, wird terminal bestätigt und verhindert Wiederaufnahme nach Reconnect; reales VM-/Gastprozess-Teardown ist Abnahmekriterium von PR 4.

---

## PR 3 — Sichere Artefakt-Upload-Sitzungen und Phasenereignisse

**Ziel:** Jobgebundene Artefakte und UI-taugliche Phasen sicher in den Core einführen.

### Dateien

- `core/src/hydrahive/compute/jobs.py` — Phasenereignisse und Zustandsübergänge.
- `core/src/hydrahive/compute/artifacts.py` — Offer, Einmal-Uploadrecht, Hash-/Quota-Prüfung und atomare Veröffentlichung.
- `core/src/hydrahive/api/routes/compute_jobs.py` — Event- und Artifact-Routen.
- `core/src/hydrahive/db/migrations/059_compute_job_artifacts.sql` — additive Metadaten-/Uploadtabellen.
- `core/tests/test_compute_game_artifacts.py` — Upload- und Inhaltsklassenprüfungen.

### TDD-Aufgaben

1. **RED:** Projektion testen: Modul-Run `created` wird beim atomaren Anlegen des Core-Jobs zu `queued`; der bestehende Core-Automat bleibt `queued → leased → running → succeeded|failed|cancelled|expired`.
2. **GREEN:** Nur erlaubte Core-Übergänge, Run-Projektionen und stabile Phasencodes implementieren.
3. **RED:** Zweiphasigen Upload testen: Offer ohne gültigen Job, falsches Projekt, abgelaufene oder wiederverwendete Session, falsche Größe und falscher Hash müssen scheitern.
4. **GREEN:** Kurzlebige Einmalrechte, serverseitigen Zielpfad und atomare Veröffentlichung implementieren.
5. **RED:** HTML, SVG, XML, JavaScript, unbekannte Medientypen, manipulierte Namen und Logs auf sichere Auslieferung testen.
6. **GREEN:** Magic-Byte-/Allowlist-Prüfung, Attachment-Auslieferung und passive Derivate durchsetzen.
7. **Commit:** `feat(compute): add game job events and artifact upload sessions`.

### Abnahmekriterien

- [ ] Prozentwerte sind optional; Phasenereignisse bleiben immer vorhanden.
- [ ] Ein Upload ist einmalig, job-/projektgebunden, quota- und hashgeprüft.
- [ ] Aktive Inhalte werden nicht inline im authentifizierten Origin gerendert.

---

## PR 4 — Node-Runner und Godot-Adapter

**Ziel:** Den bereits nachgewiesenen Linux-MicroVM-Weg als `game-runtime/v1` produktiv umsetzen.

### Dateien

- `node-agent/src/hydrahive_node/game_runtime/__init__.py` — Game-Runner-Einstieg.
- `node-agent/src/hydrahive_node/game_runtime/dispatch.py` — feste Operationsdispatch-Tabelle.
- `node-agent/src/hydrahive_node/game_runtime/staging.py` — Read-only-Quelle, Copy-on-write-Overlay, getrennte Scratch-/Cache-/Outputbereiche.
- `node-agent/src/hydrahive_node/game_runtime/godot.py` — Godot-Erkennung und typisierte Aktionen.
- `node-agent/src/hydrahive_node/game_runtime/artifacts.py` — allowlistete Output-Sammlung.
- `node-agent/src/hydrahive_node/runtime.py` — fester Providerdispatch statt der heutigen ausschließlichen Verdrahtung auf `incus.execute`.
- `node-agent/src/hydrahive_node/job_runtime.py` — Game-Handler-Cancel/Timeout, VM-Teardown und terminale Ergebnisbestätigung.
- `node-agent/tests/test_game_runtime_godot.py` — Adaptervertrag, Cancel-/Timeout- und negative Sicherheitstests.

### TDD-Aufgaben

1. **RED:** Workspace-Handle, Generation, Clean-Git-Status, Commit/Snapshot, Submodule/LFS und Inventory Snapshot als Startvoraussetzungen testen.
2. **GREEN:** Isoliertes Staging mit read-only Quelle und begrenzten Arbeitsbereichen implementieren.
3. **RED:** Godot-Inventarisierung darf `project.godot` erkennen, aber weder `@tool` noch Plugins oder Projektcode ausführen.
4. **GREEN:** Statischen Scanner mit harten Datei-/Byte-/Zeitlimits implementieren.
5. **RED:** `validate`, `test`, `build`, `run_observe` und `export` dürfen nur vorher inventarisierte IDs akzeptieren.
6. **GREEN:** Godot-Adapter mit fester Operationstabelle und `boot_smoke`-Szenario implementieren.
7. **RED:** Dirty Worktree, fremdes Artefakt, falscher Artefakthash, Netzwerkzugriff und nicht allowlistete Outputs testen.
8. **GREEN:** Fail-closed-Checks, Artefaktprovenienzprüfung und Output-Allowlist implementieren.
9. **RED:** Authentifiziertes Cancel und harter Timeout müssen VM und vollständigen Gastprozessbaum innerhalb der festgelegten Frist beenden; Reconnect darf keinen abgebrochenen Versuch wiederaufnehmen.
10. **GREEN:** Providerdispatch, Teardown und persistente terminale Ergebnisbestätigung implementieren.
11. **Commit:** `feat(node): add isolated godot game runtime`.

### Abnahmekriterien

- [ ] Godot kann ein Referenzprojekt inventarisieren, validieren, testen, exportieren und als Export beobachten.
- [ ] Importcache und generierte Dateien verändern nie den lokalen Clone.
- [ ] Unreal-Jobs werden in V0.1 mit begründetem, stabilem Fehlercode abgelehnt.

---

## PR 5 — Game-Studio-Modul: Schema und Zugriffsschutz

**Ziel:** Das installierbare Modul bekommt eigene, additive Metadaten- und Auditstrukturen; Core-Projekte bleiben autoritativ.

### Dateien

- `game-studio/manifest.json` — Modulmetadaten und Capabilities.
- `game-studio/migrations/001_game_studio.sql` — Projekte, Dokumente, Runs, Artefakte und Events.
- `game-studio/migrations/002_game_studio_indexes.sql` — Indizes und Integritätsregeln.
- `game-studio/backend/__init__.py` — Modulregistrierung.
- `game-studio/backend/access.py` — einziger `read|write|admin`-Guard.
- `game-studio/backend/models.py` und `game-studio/backend/store.py` — Modelle und Store.
- `game-studio/tests/test_game_studio_access.py` und `game-studio/tests/test_game_studio_schema.py` — Zugriff und Migrationen.

### TDD-Aufgaben

1. **RED:** Installation/Migration und vollständige Tabellenpräfixe `module_game_studio_` testen.
2. **GREEN:** Manifest, Registrierung und additive Migrationen implementieren.
3. **RED:** Für jede Ressource und jeden späteren Route-Stub Rollenmatrix sowie Cross-Project-Mismatch testen.
4. **GREEN:** Einen wiederverwendbaren Core-Projektguard implementieren; Nichtmitglieder erhalten 404, zu schwache Rollen 403.
5. **RED:** Core-Projektlöschung und Orphan-Markierung testen.
6. **GREEN:** Orphan-Projektion implementieren, ohne Membership oder Tasks zu duplizieren.
7. **Commit:** `feat(game-studio): add module schema and project access guard`.

---

## PR 6 — Game-Studio-Modul: Projekte, Dokumente und Inventarfluss

**Ziel:** Die drei Einstiege und kanonische Planungsdokumente bereitstellen.

### Dateien

- `game-studio/backend/projects.py` — neue, übernommene und Archivprojekte.
- `game-studio/backend/documents.py` — atomare, revisionsgeprüfte Dokumente.
- `game-studio/backend/resources.py` — Projektion der Core-Game-Resource.
- `game-studio/backend/routes.py` — Projekt-, Dokument-, Binding- und Inventarrouten.
- `game-studio/backend/files.py` — relative Pfade, Hashes und atomare Writes.
- `game-studio/tests/test_game_studio_projects.py`, `test_game_studio_documents.py`, `test_game_studio_inventory.py` — Flüsse und Konflikte.

### TDD-Aufgaben

1. **RED:** Neues Projekt erzeugt atomar Core-Projekt und Modulmarker; ein Teilfehler räumt kompensierend auf.
2. **GREEN:** Transaktion/kompensierendes Cleanup implementieren.
3. **RED:** Dokumentrevisionen, relative Pfade und konkurrierende Änderungen mit 409 testen.
4. **GREEN:** Kanonischen `game-studio/`-Dokumentbereich mit atomaren Writes implementieren.
5. **RED:** Adopt-/Archive-Flow darf nur registrierte opaque Handles nutzen; `inventory_only` darf keine Engineausführung auslösen.
6. **GREEN:** Ressourcenprojektion und statischen Inventarstart implementieren.
7. **RED:** Vollständige Dateinamen sind ohne ausdrückliche Privacy-Freigabe nicht sichtbar.
8. **GREEN:** Zusammenfassungs- und `full_names`-Privacy-Modus implementieren.
9. **Commit:** `feat(game-studio): add project documents and inventory flows`.

---

## PR 7 — Game-Studio-Modul: Runs, Artefakte und Aktivität

**Ziel:** Fachliche Projektion der Core-Jobs in sichere, nachvollziehbare Game-Studio-Ansichten.

### Dateien

- `game-studio/backend/runs.py` — Run-Projektion und Core-Job-Verknüpfung.
- `game-studio/backend/artifacts.py` — Modulmetadaten und sichere Lesemodelle.
- `game-studio/backend/routes.py` — Runs, Events, Cancel und Artefakte ergänzen.
- `game-studio/tests/test_game_studio_runs.py` und `test_game_studio_artifacts.py` — Projektion, Cancel und XSS-Gegenproben.

### TDD-Aufgaben

1. **RED:** Ein Run muss Projekt, Resource, Binding, Engineprofil, Inputrevision, Phase, Dauer, Fehler und Artefakte korrekt referenzieren.
2. **GREEN:** Run-/Event-Projektion aus Core-Ereignissen implementieren.
3. **RED:** Cancel ohne Rollenrecht, falsches Projekt oder nicht abbrechbaren Job testen.
4. **GREEN:** Cancel über den Core-Vertrag und auditierte Ereignisse implementieren.
5. **RED:** Artefaktlisten mit HTML/SVG/XML, gefälschtem Medientyp, manipuliertem Namen und Log-HTML testen.
6. **GREEN:** Nur sichere Detailmodelle, Downloadlinks und passive Vorschau-Derivate ausgeben.
7. **Commit:** `feat(game-studio): project runs artifacts and activity`.

---

## PR 8 — Game-Studio-Frontend: Übersicht und Guided Flow

**Ziel:** Projektübersicht, drei Einstiege und die fünf geführten Schritte bereitstellen.

### Dateien

- `game-studio/frontend/index.tsx` — Routen, Navigation und i18n-Export.
- `game-studio/frontend/GameStudioPage.tsx` — CockpitShell und CockpitTopbar.
- `game-studio/frontend/api.ts` und `game-studio/frontend/types.ts` — API-Vertrag.
- `game-studio/frontend/project/ProjectOverview.tsx` — Liste, Status und nächster Schritt.
- `game-studio/frontend/project/CreateGameDialog.tsx`, `AdoptProjectDialog.tsx`, `InspectArchiveDialog.tsx` — drei Einstiege.
- `game-studio/frontend/guided/GuidedGameFlow.tsx` und `Step*.tsx` — fünf Schritte.
- `game-studio/frontend/i18n.ts` — Deutsch/Englisch.
- `game-studio/tests/frontend/*.test.tsx` — Seiten- und Flowtests.

### TDD-Aufgaben

1. **RED:** Routen-, Rechte- und Leerzustandstests für Übersicht und Projektkopf schreiben.
2. **GREEN:** CockpitShell/CockpitTopbar, Projektliste und serverseitig gefilterte Darstellung implementieren.
3. **RED:** Je einen Test für neuen, übernommenen und Archivfluss schreiben; Engineaktionen ohne Workstation müssen sichtbar begründet deaktiviert sein.
4. **GREEN:** Die drei Dialoge mit semantischem Dialograhmen und Fokusmanagement implementieren.
5. **RED:** Fünf-Schritte-Flow testen: fehlende Voraussetzungen blockieren nicht stumm, sondern nennen konkret den nächsten Bedarf.
6. **GREEN:** Guided Flow, Fortschritt und `NOT_ASSESSED`-Playtestentscheidung implementieren.
7. **RED:** i18n-Parität Deutsch/Englisch und fehlende `aria-label`-/Label-Fälle testen.
8. **GREEN:** Namespace-Bundle, lokalisierte Status-/Fehlercodes und vollständige Beschriftungen implementieren.
9. **Commit:** `feat(game-studio): add overview and guided project flow`.

---

## PR 9 — Game-Studio-Frontend: Werkbank, Jobs und Artefakte

**Ziel:** Die reguläre Arbeitsfläche mit zugänglichen Tabs, Aktivitäten und Artefakten ausbauen.

### Dateien

- `game-studio/frontend/workbench/GameWorkbench.tsx` — semantische Tabs.
- `game-studio/frontend/workbench/DesignTab.tsx`, `ProductionTab.tsx`, `EngineTab.tsx`, `PlaytestTab.tsx`, `TeamTab.tsx` — Werkbankbereiche.
- `game-studio/frontend/jobs/RunList.tsx`, `RunDetail.tsx`, `JobPhase.tsx` — Phasen, Dauer, Fehler und Cancel.
- `game-studio/frontend/artifacts/ArtifactGallery.tsx`, `ArtifactCard.tsx`, `ArtifactDetail.tsx` — sichere Artefaktansichten.
- `game-studio/tests/frontend/workbench.test.tsx`, `jobs.test.tsx`, `artifacts.test.tsx`, `responsive.test.tsx` — UI-Abnahme.

### TDD-Aufgaben

1. **RED:** WAI-ARIA-Tests für `tablist`, `tab`, `tabpanel`, Auswahlzustand, Pfeiltasten und Fokus schreiben.
2. **GREEN:** Werkbank mit echten Tabs und unter `xl` umschaltbaren Paneelen implementieren.
3. **RED:** Run-Tests für Phase ohne Prozent, Prozent mit echtem Nenner, Fehler, Cancel und Abschluss-`aria-live` schreiben.
4. **GREEN:** Runliste/-detail mit Rollen- und Statusabhängigkeit implementieren.
5. **RED:** Artefakt-Tests für passive Vorschau, serverseitigen Download und keine Inline-Vorschau für aktive/unsichere Inhalte schreiben.
6. **GREEN:** Galerie, Detailansicht, Herkunft, Hash, Größe und Workstation-/HydraHive-Speicherort implementieren.
7. **RED:** Browser-/Komponententest für 320 px, sichtbaren Fokus, Dialogfokusfalle und `prefers-reduced-motion` schreiben.
8. **GREEN:** Responsive Styles, Fokus- und Bewegungsregeln implementieren.
9. **Commit:** `feat(game-studio): add accessible workbench jobs and artifacts`.

---

## PR 10 — Agenten-/Skillpaket und Provenienz

**Ziel:** Kuratierte, begrenzte Agentenarbeit mit nachvollziehbarer Herkunft bereitstellen.

### Dateien

- `game-studio/skills/` — neun schlanke Game-Workflows.
- `game-studio/UPSTREAM.md` — Upstream-Herkunft, MIT-Hinweise und Anpassungen.
- `game-studio/backend/tools.py` — rollen- und projektgebundene Agententools.
- `game-studio/backend/agent_profile.py` — Core-verwaltetes Projektagentenprofil mit fester Tool-/Credential-Grenze und `managed_by="game-studio"`.
- `game-studio/tests/test_game_studio_tools.py` und `test_game_studio_agent_profile.py` — Tool-, Profil-, Projektbindungs- und Provenienzgrenzen.

### TDD-Aufgaben

1. **RED:** Gegen den realen Core-Agentenvertrag testen: der normale automatische Projektagent mit `shell_exec` darf nicht als Game-Studio-Agent gelten oder Game-Jobs starten.
2. **GREEN:** Game-Studio-verwaltetes Agentenprofil mit Projektbindung, Profilversion und fester Tool-Allowlist ohne `shell_exec`, freie MCP-/Plugins und Credential-Injektion registrieren.
3. **RED:** Änderungen an Toolliste, Projektbindung, Systemprompt oder `managed_by` außerhalb des autorisierten Adminpfads müssen scheitern und auditiert werden.
4. **GREEN:** Profilintegrität und Admin-Updatepfad implementieren.
5. **RED:** Tests schreiben, dass Agententools weder freie Shell, Credentials, absolute Pfade noch projektfremde Ressourcen sehen.
6. **GREEN:** Tooloberfläche auf dokumentierte Projektdateien, Aufgaben, Runstart und sichere Ergebnislesung begrenzen.
7. **RED:** Test schreiben, dass ein Adopt-Workflow bestehende Artefakte nur referenziert und nie still regeneriert/überschreibt.
8. **GREEN:** Ergänzungsplan- und explizite-Bestätigungslogik implementieren.
9. **RED:** Lizenz-/Herkunftstest für jede substantielle Upstream-Übernahme schreiben.
10. **GREEN:** `UPSTREAM.md` und nachvollziehbare Anpassungsnachweise ergänzen.
11. **Commit:** `feat(game-studio): add curated agent workflows and provenance`.

---

## PR 11 — Ende-zu-Ende-Abnahme

**Ziel:** Die Akzeptanzkriterien gegen reale, isolierte Referenzfälle belegen.

### Referenzfälle

- frisches kleines Godot-Projekt;
- bestehendes Godot-Projekt;
- frisches und bestehendes Unreal-Projekt jeweils ausschließlich `inventory_only`;
- präpariertes Archiv mit Traversal, Symlink, Sonderdatei, Verschachtelung und Bombenindikatoren;
- Rollenmatrix mit Nichtmitglied, `read`, `write` und `admin`.

### TDD-/Abnahmeaufgaben

1. **RED:** E2E-Tests für Projektanlage, Berechtigungen, Inventar, Godot-Job, Cancel, Artefaktannahme und Playtest-Evidenz anlegen.
2. **GREEN:** Fehlende Integrationspunkte nur dann ergänzen, wenn sie einen konkreten roten E2E-Test grün machen.
3. **RED:** Sicherheitsgegenproben für Prompt-Injection in Projektdateien, Logs und Archiven sowie Stored-XSS in Artefakten ausführen.
4. **GREEN:** Regressionsschutz und dokumentierte Ablehnungsgründe ergänzen.
5. **Nachweis:** Testausgaben, Screenshots und reale `boot_smoke`-Evidenz in einem Abnahmebericht festhalten.
6. **Commit:** `test(game-studio): add end-to-end acceptance coverage` und `docs(game-studio): record v0.1 acceptance evidence`.

## Globale Akzeptanzkriterien

- [ ] Die 23 Kriterien aus `docs/specs/game-studio-module-v0.1.md` §28 sind erfüllt, mit der beschlossenen Anpassung: Unreal bleibt V0.1 `inventory_only`.
- [ ] Jeder produktive Game-Job ist projekt-, resource-, generation-, Quellstand-, Snapshot-, Lease- und signaturgebunden.
- [ ] Kein Projektcode, Plugin, Archiv oder Artefakt kann Hostausführung, Secrets, Netzwerk oder Zugriff auf Geschwisterprojekte erzwingen.
- [ ] Godot-Referenzprojekte können isoliert inventarisiert, validiert, getestet, exportiert und beobachtet werden.
- [ ] UI erfüllt Deutsch/Englisch, Tastaturbedienung, Fokus, Kontrast, reduzierte Bewegung und 320-px-Layout.
- [ ] Alle Tests laufen grün; keine Freigabe allein auf Basis von Mock-Ergebnissen.
