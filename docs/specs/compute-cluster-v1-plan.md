# Plan: HydraHive Compute Cluster V1

**Stand: 17. Juli 2026 — P1 bis P4 implementiert; P5 bis P7 offen.**

## Ziel

HydraHive verwaltet neben dem lokalen Host freigegebene Ubuntu-Compute-Nodes mit ausgehend verbundenem Node Agent und Incus. V1 liefert manuelle, feste Platzierung, Remote-Container und imagebasierte Remote-VMs ohne Live-Migration oder automatisches Failover.

Verbindliche Grundlage: `docs/specs/compute-cluster-v1.md`.

## Lieferstrategie

Die Umsetzung erfolgt in getrennten, jeweils produktionsfähigen PRs. Kein PR darf bestehende lokale Container oder QEMU-VMs brechen.

1. P1 — Compute-Node-Datenmodell und lokale Kompatibilität
2. P2 — Enrollment, Identität und read-only Agentkanal
3. P3 — Persistente Compute-Jobs
4. P4 — Remote-Container
5. P5 — Node-/Job-Frontend
6. P6 — Imagebasierte Remote-VMs
7. P7 — Console-Proxy, Hardening und V1-Abschluss

## Neue Hauptbereiche

### Master Backend

- `core/src/hydrahive/compute/models.py` — Node-, Enrollment-, Job- und Eventtypen.
- `core/src/hydrahive/compute/db.py` — parametrisierter Datenzugriff.
- `core/src/hydrahive/compute/enrollment.py` — Token/HMAC, CSR, Zertifikat und Freigabe.
- `core/src/hydrahive/compute/identity.py` — Compute-CA, Fingerprints, Signatur und Widerruf.
- `core/src/hydrahive/compute/protocol.py` — versionierte Agentnachrichten.
- `core/src/hydrahive/compute/jobs.py` — Jobzustandsmaschine, Lease und Idempotenz.
- `core/src/hydrahive/compute/agent_channel.py` — authentisierter Agentkanal.
- `core/src/hydrahive/compute/capabilities.py` — Capability-/Health-Normalisierung.
- `core/src/hydrahive/api/routes/compute_nodes.py` — Admin-Node-API.
- `core/src/hydrahive/api/routes/compute_jobs.py` — Admin-/User-Job-API.
- `core/src/hydrahive/api/routes/compute_agent.py` — Enrollment und Agentkanal.
- `core/src/hydrahive/db/migrations/032_compute_nodes.sql` bis `039_compute_placement_integrity.sql` — additive, wiederaufnehmbare Clusterbasis.

### Node Agent

- `node-agent/pyproject.toml` — separates minimales Paket und CLI-Entrypoint.
- `node-agent/src/hydrahive_node/config.py` — restriktive Konfiguration.
- `node-agent/src/hydrahive_node/identity.py` — Schlüssel, CSR und Zertifikate.
- `node-agent/src/hydrahive_node/enroll.py` — Enrollment-CLI.
- `node-agent/src/hydrahive_node/client.py` — Reconnect-/ACK-Agentkanal.
- `node-agent/src/hydrahive_node/capabilities.py` — Host-/Incus-/KVM-Inventar.
- `node-agent/src/hydrahive_node/jobs.py` — lokale Idempotenz und Dispatcher.
- `node-agent/src/hydrahive_node/incus.py` — allowlisteter Incus-CLI-Adapter.
- `node-agent/src/hydrahive_node/main.py` — systemd-Prozess.
- `installer/lib/node_agent.sh` — Installation, Benutzer, Rechte und systemd-Unit.

### Frontend

- `frontend/src/features/nodes/api.ts`
- `frontend/src/features/nodes/types.ts`
- `frontend/src/features/nodes/NodeStatusBadge.tsx`
- `frontend/src/features/nodes/NodeSelector.tsx`
- `frontend/src/features/cockpit/admin/NodesOverlay.tsx`
- `frontend/src/features/cockpit/admin/NodeDetailOverlay.tsx`
- `frontend/src/features/cockpit/admin/JobsOverlay.tsx`
- `frontend/src/features/cockpit/admin/adminOverlayRegistry.ts`
- bestehende Container-/VM-Create-Dialoge, Karten und Overlays.

## Implementierungsreihenfolge

## P1 — Compute-Node-Datenmodell und lokale Kompatibilität

### Task 1.1: Migration und Modelle

- [x] Test schreiben: Migration erzeugt `compute_nodes`, `compute_enrollment_tokens`, `compute_jobs`, `compute_job_events`.
- [x] Test schreiben: `local` wird genau einmal angelegt.
- [x] Test schreiben: bestehende VMs/Container erhalten `node_id='local'` und `generation=0`.
- [x] Tests RED ausführen.
- [x] Migrationsserie `032` bis `039` additiv und nach Teilfehlern wiederaufnehmbar implementieren.
- [x] `compute/models.py` mit strikten Status-Literalen und Grenzen implementieren.
- [x] Tests GREEN ausführen.
- [x] Commit: `feat(compute): add node and job schema`.

### Task 1.2: Node-Repository

- [x] Tests für Create/List/Get/Update, eindeutige Namen, Statusübergänge und JSON-Grenzen schreiben.
- [x] Tests RED.
- [x] `compute/db.py` mit ausschließlich parametrisierten Queries implementieren.
- [x] Reservierten `local`-Node gegen Delete/Revoke schützen.
- [x] Tests GREEN.
- [x] Commit: `feat(compute): add node registry persistence`.

### Task 1.3: Bestehende Ressourcen nodefähig machen

- [x] Tests für Container-/VM-Serialisierung mit `node_id` schreiben.
- [x] Tests sichern, dass alte Create-Payloads ohne `node_id` lokal bleiben.
- [x] Dataclasses, DB-Mapper und API-Typen additiv erweitern.
- [x] Reconciler filtern strikt `node_id='local'`, damit Remote-Ressourcen nie lokal ausgeführt werden.
- [x] Bestehende Container-/VM-Suite GREEN.
- [x] Commit: `feat(compute): bind resources to local node`.

**P1-Akzeptanz:** Alle Bestandsressourcen verhalten sich unverändert; API-Antworten enthalten zusätzlich den lokalen Node.

## P2 — Enrollment, Identität und read-only Agentkanal

### Task 2.1: Compute-CA und Enrollment-Token

- [x] Tests für 256-Bit-Token, HMAC-at-rest, TTL, Einmalverbrauch und generische Fehler schreiben.
- [x] Tests für sichere CA-Key-Dateirechte und stabile Fingerprints schreiben.
- [x] Tests RED.
- [x] `identity.py` und `enrollment.py` implementieren.
- [x] Keine privaten Schlüssel oder Tokens loggen.
- [x] Tests GREEN.
- [x] Security-Review.
- [x] Commit: `feat(compute): add secure node enrollment`.

### Task 2.2: Enrollment-/Node-API

- [x] Auth-/Admin-/Rate-Limit-Tests schreiben.
- [x] Tests für pending → approved, disable und revoke schreiben.
- [x] Tests RED.
- [x] `compute_nodes.py` und öffentlichen, begrenzten Enroll-Endpunkt implementieren.
- [x] Audit für Token-Erzeugung, Enrollment, Approve und Revoke.
- [x] Tests GREEN.
- [x] Commit: `feat(compute): expose node administration api`.

### Task 2.3: Minimales Agentpaket

- [x] Agenttests für Config-Dateirechte, Enrollment, Serverzertifikatprüfung und Fingerprintanzeige schreiben.
- [x] Tests RED.
- [x] Separates `node-agent`-Paket implementieren.
- [x] `hydrahive-node enroll` und `hydrahive-node run` bereitstellen.
- [x] systemd-Unit und Installer implementieren.
- [x] Tests GREEN.
- [x] Commit: `feat(node-agent): add enrollment and service`.

### Task 2.4: Heartbeat und Capabilities

- [x] Protokolltests für Version, Sequenz, Nonce, Node-Bindung und Schemafehler schreiben.
- [x] Tests für online/degraded/offline und Dead-Detection schreiben.
- [x] Tests RED.
- [x] Agentkanal mit Reconnect/Jitter und read-only Heartbeats implementieren.
- [x] CPU/RAM/Storage/Incus/KVM-Capabilities implementieren.
- [x] Tests GREEN.
- [x] Commit: `feat(compute): connect node agent heartbeats`.

**P2-Akzeptanz:** Ein neuer Ubuntu-Node kann sicher gekoppelt, freigegeben, angezeigt und widerrufen werden; noch keine Workloads.

## P3 — Persistente Compute-Jobs

### Task 3.1: Jobzustandsmaschine

- [x] Tests für erlaubte Übergänge, atomaren Claim, Lease, Timeout und Cancel schreiben.
- [x] Tests für doppelte Resultate und Idempotency-Key schreiben.
- [x] Tests RED.
- [x] `compute/jobs.py` und Event-Persistenz implementieren.
- [x] Tests GREEN.
- [x] Commit: `feat(compute): add durable job state machine`.

### Task 3.2: Signierte Jobs und Agentdispatcher

- [x] Tests für manipulierte Signatur, falsche Node-ID, alte Generation und Ablauf schreiben.
- [x] Tests RED.
- [x] kanonische Job-Signatur auf Master und Prüfung im Agent implementieren.
- [x] Agent persistiert lokale Idempotency-Keys.
- [x] Nur typisierte Operationen; unbekannte Operation fail-closed.
- [x] Tests GREEN.
- [x] Security-Review.
- [x] Commit: `feat(node-agent): execute signed compute jobs`.

### Task 3.3: Job-API

- [x] Ownership-/Admin-/Filter-/Cancel-Tests schreiben.
- [x] Tests RED.
- [x] `compute_jobs.py` implementieren.
- [x] Ausgabe strikt begrenzen und keine Payload-Secrets zurückgeben.
- [x] Tests GREEN.
- [x] Commit: `feat(compute): expose job status api`.

**P3-Akzeptanz:** Ein Testjob übersteht Agent-Reconnect ohne doppelte Ausführung und besitzt vollständigen Auditverlauf.

## P4 — Remote-Container

### Task 4.1: Incus-Allowlist im Agent

- [x] Tests für Name/Image/CPU/RAM/Netzwerk-Validierung und Flag-Injection schreiben.
- [x] Tests für create/start/stop/restart/delete/inspect schreiben, Incus mocken.
- [x] Tests RED.
- [x] `node-agent/.../incus.py` mit `create_subprocess_exec` und festen argv implementieren.
- [x] Output-, Zeit- und Parallelitätslimits implementieren.
- [x] Tests GREEN.
- [x] Security-Review.
- [x] Commit: `feat(node-agent): manage incus containers`.

### Task 4.2: Container-Execution-Routing

- [x] Tests schreiben: local nutzt bisherigen Pfad, agent erzeugt Job, offline wird abgelehnt.
- [x] Reconciler-Test: Remote-Container wird nie lokal inspiziert/gestartet.
- [x] Tests RED.
- [x] lokalen und Agent-Execution-Adapter einführen.
- [x] Create/Lifecycle-Routen nodefähig machen.
- [x] Tests GREEN.
- [x] Commit: `feat(containers): route workloads to compute nodes`.

**P4-Akzeptanz:** Ein Remote-Container kann über HydraHive vollständig verwaltet werden; lokale Container bleiben kompatibel.

## P5 — Node-/Job-Frontend

### Task 5.1: Nodes-Overlay

- [ ] API-/Mappertests und Komponentenfälle pending/online/degraded/offline/revoked schreiben.
- [ ] NodesOverlay, Detail, Enrollment und Fingerprint-Approve implementieren.
- [ ] Admin-Registry und Help ergänzen.
- [ ] Frontend-Typecheck/Build GREEN.
- [ ] Commit: `feat(admin): add compute node cockpit`.

### Task 5.2: Job-Overlay

- [ ] Zustands-/Fortschritts-/Fehlerfälle testen.
- [ ] JobsOverlay und Jobdetail implementieren.
- [ ] Cancel nur in zulässigen Zuständen anbieten.
- [ ] Build GREEN.
- [ ] Commit: `feat(admin): add compute job monitoring`.

### Task 5.3: Container-Node-Auswahl

- [ ] NodeSelector-Fälle online/offline/ungeeignet testen.
- [ ] CreateContainerDialog um Pflichtauswahl mit Default `local` erweitern.
- [ ] Karten/Details um Node-Badge ergänzen.
- [ ] Build GREEN.
- [ ] Commit: `feat(containers): select target compute node`.

## P6 — Imagebasierte Remote-VMs

### Task 6.1: Incus-VM-Operationen

- [ ] Agenttests für KVM-Capability und `--vm`-Erstellung schreiben.
- [ ] create/start/stop/restart/delete/inspect implementieren.
- [ ] ISO, Import, Hostpfade und Passthrough auf Agent-Nodes explizit ablehnen.
- [ ] Tests GREEN.
- [ ] Commit: `feat(node-agent): manage incus virtual machines`.

### Task 6.2: VM-Execution-Routing

- [ ] Tests local QEMU vs. remote Incus schreiben.
- [ ] VM-Modelle um `runtime`/`runtime_ref` erweitern.
- [ ] Remote-Lifecycle und Snapshots nodegebunden implementieren.
- [ ] Reconciler filtert strikt nach Node/Runtime.
- [ ] Bestehende VM-Suite GREEN.
- [ ] Commit: `feat(vms): route image vms to compute nodes`.

### Task 6.3: VM-Frontend

- [ ] NodeSelector und Capability-Erklärung integrieren.
- [ ] Auf Agent-Nodes ausschließlich kuratierte Images anbieten.
- [ ] ISO/Import/Passthrough disabled mit verständlicher Begründung.
- [ ] Node-Badge und Offline-Semantik ergänzen.
- [ ] Build GREEN.
- [ ] Commit: `feat(vms): select target compute node`.

## P7 — Console-Proxy und V1-Abschluss

### Task 7.1: Ressourcengebundene Console-Tickets

- [ ] Auth-, Ownership-, TTL-, Einmal- und Origin-Tests schreiben.
- [ ] Keine direkten Node-Ports; binärer Stream über authentisierten Master-Proxy.
- [ ] Revoke/Disconnect trennt Sessions.
- [ ] Security-Review und Tests GREEN.
- [ ] Commit: `feat(compute): proxy remote instance consoles`.

### Task 7.2: Hardening und Updatepfad

- [ ] Revocation-E2E-Test.
- [ ] kompromittierter/falscher Node kann keine fremden Jobs lesen.
- [ ] signiertes Agent-Update-Manifest und Hashprüfung implementieren.
- [ ] Last-/Reconnect-/Lease-Tests.
- [ ] Auditprüfung.
- [ ] Commit: `feat(node-agent): harden revocation and updates`.

### Task 7.3: Abschluss

- [ ] vollständige Backend-, Agent- und Frontendtests.
- [ ] Installer-Test auf frischem Ubuntu-Node.
- [ ] realer E2E-Test mit einem separaten Compute-Node.
- [ ] Security-Audit ohne Critical/High-Findings.
- [ ] Betriebs-, Recovery- und Deinstallationsdoku.
- [ ] PRs mergen und Tasks schließen.

## Globale Akzeptanzkriterien

- [ ] Kein Remote-Agent akzeptiert freie Shell-Befehle.
- [ ] Jeder Node hat eine eigene widerrufbare Identität.
- [ ] Bestehende lokale Instanzen funktionieren ohne manuelle Migration.
- [ ] Jobs sind persistent, idempotent und auditierbar.
- [ ] Node-Ausfall wird korrekt dargestellt und löst keine Doppelstarts aus.
- [ ] Remote-Container und imagebasierte Remote-VMs sind über HydraHive steuerbar.
- [ ] Keine Live-Migration, kein HA und kein automatischer Scheduler in V1.
