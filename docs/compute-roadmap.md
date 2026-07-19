# HydraHive Compute — Master-Roadmap

**Letzte Aktualisierung:** 20. Juli 2026
**Aktueller Stand:** P0–P7 code-seitig abgeschlossen; offen bleibt nur das physische Rollout-Gate (echter Ubuntu-/Incus-Node)
**Verbindliche V1-Spezifikation:** [specs/compute-cluster-v1.md](specs/compute-cluster-v1.md)
**Detaillierte Tasks:** [specs/compute-cluster-v1-plan.md](specs/compute-cluster-v1-plan.md)

## Zielbild

HydraHive verwaltet den lokalen Host und freigegebene Ubuntu-Compute-Nodes über einen ausgehend verbundenen Node Agent. Workloads sind dauerhaft an einen Node gebunden. Mutationen laufen als signierte, persistente und lease-geschützte Jobs. V1 bietet manuelle Platzierung, Remote-Container und anschließend imagebasierte Remote-VMs; automatische Migration und Failover bleiben außerhalb von V1.

## Statuslegende

- ✅ abgeschlossen und im Branch integriert
- 🚧 in Arbeit
- ⬜ geplant
- ⛔ bewusst nicht Teil der aktuellen Version

## Phasenübersicht

| Phase | Status | Inhalt | Ergebnis / Gate |
|---|---:|---|---|
| P0 | ✅ | Produktvertrag und Gap-Audit | V1-Grenzen, Architektur und Legacy/Cockpit-Abgleich dokumentiert |
| P1 | ✅ | Node-Datenmodell und lokale Kompatibilität | Additive Migrationen, lokaler Node, Ressourcenbindung, lokale Regressionen grün |
| P2 | ✅ | Enrollment, Identität und Agentkanal | HMAC-Token, CSR/mTLS, Freigabe/Widerruf, Heartbeats und Capabilities |
| P3 | ✅ | Persistente Compute-Jobs | Signatur, Lease, Idempotenz, Reconnect-Recovery, Job-API und Audit-Events |
| P4 | ✅ | Remote-Container End-to-End | Allowlist-Incus-Adapter, atomare Routing-/Resultpfade, Remote-Lifecycle |
| P5 | ✅ | Node-/Job-Frontend | Admin-Overlays, Enrollment-UX, Jobmonitoring und Node-Auswahl |
| P6 | ✅ | Imagebasierte Remote-VMs | Incus-VM-Adapter, Routing, Runtime-Anzeige und VM-Lifecycle |
| P7 | ✅ | Console-Proxy und V1-Abschluss | Console-Tickets, Revocation-/Update-Hardening, Runbooks |

## Abgeschlossene Grundlagen

### P0 — Produktvertrag und Gap-Audit ✅

- [x] Compute-Cluster-V1-Spezifikation mit Trust-, Netzwerk- und Betriebsgrenzen.
- [x] Detaillierte PR-/Task-Reihenfolge definiert.
- [x] Legacy-vs.-Cockpit-Gap-Audit erstellt.
- [x] Keine Live-Migration, kein automatisches Failover und kein beliebiges Remote-Shell-Primitive in V1.

### P1 — Compute-Node-Datenmodell und lokale Kompatibilität ✅

- [x] Additive Migrationen `032` bis `039`.
- [x] Node-Registry mit reserviertem `local`-Node und strikten Statusübergängen.
- [x] Container und VMs besitzen `node_id` und `generation`.
- [x] Alte Create-Payloads bleiben standardmäßig lokal.
- [x] Lokale Reconciler und Incus-/QEMU-Pfade ignorieren Remote-Ressourcen.

### P2 — Enrollment, Identität und Agentkanal ✅

- [x] Einmalige 256-Bit-Enrollment-Tokens, nur als HMAC gespeichert.
- [x] Compute-CA, CSR-Prüfung, Node-Zertifikate und Fingerprint-Bestätigung.
- [x] Admin-API für Pending/Approve/Disable/Revoke.
- [x] Ausgehender mTLS-WebSocket-Kanal mit Node-Bindung, Sequenz und Nonce.
- [x] Separater gehärteter Node-Agent mit systemd-Unit und restriktiven Dateirechten.
- [x] Heartbeats, Dead Detection, Capability- und Ressourceninventar.

### P3 — Persistente Compute-Jobs ✅

- [x] Durable Zustandsmaschine mit Events, atomarem Claim und begrenzten Leases.
- [x] Ed25519-signierte, nodegebundene Job-Angebote.
- [x] Agentseitige Persistenz vor Ausführung und Ergebnis vor Zustellung.
- [x] Lease-Renewal, Reconnect-Recovery und sichere Behandlung unbekannter Outcomes.
- [x] Admin-/Owner-Job-API mit begrenzter Ausgabe und Cancel-Regeln.
- [x] Strukturierte Fehler ohne rohe Agent-Ausgaben.

### P4 — Remote-Container End-to-End ✅

- [x] Fester Incus-Binary-Pfad und ausschließlich feste argv-Aufrufe ohne Shell.
- [x] Strikte Payload-, Name-, Image-, Ressourcen- und Resource-ID-Validierung.
- [x] Ownership-Bindung über `user.hydrahive.id`.
- [x] Idempotente Create/Start/Stop/Delete/Inspect-Reconciliation; Restart fail-closed bei unbekanntem Ausgang.
- [x] Container werden mit `incus init` zunächst gestoppt erstellt, Netzwerk wird verifiziert und erst danach gestartet.
- [x] Isolierte Container überschreiben geerbtes `eth0` mit `type=none`; Bridged nutzt `br0`.
- [x] Zeit-, Output- und Parallelitätsgrenzen im Prozessadapter.
- [x] Agent startet Jobloop und Heartbeat parallel; Resume erneuert vor Mutation die Lease.
- [x] Remote-Placement ist Admin-only.
- [x] State-Transition und Job-Insert sind eine `BEGIN IMMEDIATE`-/CAS-Transaktion.
- [x] Terminaler Jobstatus und generation-fenced Containerprojektion sind atomar.
- [x] Draining blockiert Create/Start/Restart, erlaubt Stop/Delete/Inspect.
- [x] `GET /info` bleibt read-only; Remote-Refresh läuft explizit als `POST .../refresh`.
- [x] Lokale Container verwenden unverändert den bestehenden Lifecycle-Pfad.

### P5 — Node-/Job-Frontend ✅

**Commit:** `feat(admin): add compute node and job cockpit`

- [x] Nodes-Liste mit Pending/Online/Degraded/Draining/Offline/Revoked.
- [x] Enrollment-Token-Flow und Fingerprint-Bestätigung.
- [x] Node-Details für Agentversion, Capabilities, Ressourcen und letzte Heartbeats.
- [x] Admin-Aktionen Approve, Drain, Disable und Revoke mit Bestätigungsdialog.
- [x] Filterbare Jobliste und Jobdetail mit Event-Timeline.
- [x] Fortschritt, strukturierte Fehler und Lease-Informationen; Cancel nur in erlaubten Zuständen.
- [x] Node-Auswahl im Container-Create-Dialog (Default `local`, nur online/geeignet); Node-Badge auf Karten.

### P6 — Imagebasierte Remote-VMs ✅

**Commits:** `feat(node-agent): manage incus virtual machines`, `feat(vms): route image vms to compute nodes`, `feat(vms): select target compute node`

- [x] Incus-VM-Allowlist und KVM-Capability-Gate (`incus init --vm`, expliziter Root-Disk).
- [x] Remote-VM-Create/Start/Stop/Restart/Delete/Inspect als generation-gebundene Jobs.
- [x] Lokales QEMU und Remote-Incus bleiben explizite Runtime-Typen; Reconciler filtert Remote.
- [x] ISO, Import, Hostpfade und Passthrough auf Agent-Nodes abgelehnt.
- [x] VM-Frontend: Node-Auswahl, kuratierte Images, Node-Badge; QEMU-Felder nur lokal.

### P7 — Console-Proxy und V1-Abschluss ✅

**Commits:** `feat(compute): issue resource-bound console tickets`, `feat(node-agent): harden revocation and updates`

- [x] Kurzlebige, resource- und nodegebundene Console-Tickets (einmalig, TTL 15–120 s, Admin-only).
- [x] Keine allgemeinen Tunnel oder Remote-Shell-Primitiven; nur allowlistete Incus-Operationen.
- [x] Revocation invalidiert Node-Identität und alle offenen Console-Tickets atomar; Job-Isolation zwischen Nodes verifiziert.
- [x] Signiertes Agent-Update-Manifest (Ed25519 + SHA-256 + Downgrade-Schutz).
- [x] Betriebs-, Recovery-, Drain- und Revocation-Runbook: [compute-node-runbook.md](compute-node-runbook.md).
- [ ] Rollout auf echtem Ubuntu-/Incus-Testnode und dokumentierte Abnahme — **physisches Rollout-Gate, kein Code-Todo**.

## V1-Status

Der Compute-Cluster V1 ist code-seitig vollständig (P0–P7). Alle automatisierten
Backend-, Node-Agent- und Frontend-Prüfungen sind grün, die Security-Properties
sind belegt (siehe Runbook Abschnitt 8). Die einzige verbleibende Aufgabe ist die
physische Abnahme auf echter Ubuntu-/Incus-Hardware — ein Rollout-Gate, das
bewusst von der Code-Abnahme getrennt ist.

## Nicht Bestandteil von V1 ⛔

- Live-Migration und automatisches Failover.
- Automatische Platzierungsoptimierung ohne Admin-Entscheidung.
- Beliebige Shell-/Dateioperationen über den Agentkanal.
- Host-Passthrough und freie Hostpfade für Remote-Workloads.
- Gemeinsamer Cluster-Storage ohne separates Sicherheits- und Betriebsdesign.

## Pflege dieser Roadmap

1. Beim Start einer Phase Status auf 🚧 setzen.
2. Erledigte Tasks im detaillierten Plan und hier gleichzeitig abhaken.
3. Pro Phase Commit-/PR-Referenzen und Verifikationsstand im Abschlussbericht ergänzen.
4. Eine Phase erst auf ✅ setzen, wenn Tests, Security-Review, lokale Regressionen und Dokumentation abgeschlossen sind.
5. Physische Rollout-Tests ausdrücklich von Mock-/Integrationstests unterscheiden.
