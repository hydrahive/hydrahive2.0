# Compute-Implementierungsabschluss P5–P7

**Datum:** 20. Juli 2026
**Branch:** `feat/remote-containers`
**Umfang:** Node-/Job-Frontend, imagebasierte Remote-VMs, Console-Tickets und Hardening

## Kurzfazit

Die Phasen P5 bis P7 der Compute-Cluster-V1-Planung sind im Code umgesetzt.
Zusammen mit P1–P4 ist HydraHive Compute V1 damit code-seitig vollständig:
Admins koppeln, überwachen und widerrufen Nodes über das Cockpit, platzieren
Container und imagebasierte VMs gezielt auf Remote-Nodes, verfolgen Jobs mit
Event-Timeline und öffnen Konsolen über kurzlebige, ressourcengebundene Tickets.

Alle automatisierten Prüfungen sind grün. Die physische Abnahme auf echter
Ubuntu-/Incus-Hardware bleibt ein ausdrückliches Rollout-Gate.

## P5 — Node-/Job-Frontend

**Commit:** `feat(admin): add compute node and job cockpit`

- `features/nodes` (API, Typen, Status-Badge, Node-Karte, Node-Selector,
  Enroll-/Approve-/Detail-Dialoge) und `features/jobs` (API, Typen, Status-Badge,
  filterbare Liste, Detail mit Event-Timeline und zustandsgesteuertem Cancel).
- `NodesOverlay` und `JobsOverlay` in der Admin-Cockpit-Registry verdrahtet.
- Container-Create-Dialog um Admin-only Ziel-Node-Auswahl (Default `local`)
  erweitert; Container-Karten zeigen ein Remote-Node-Badge.
- Vollständige de/en-Lokalisierung und Hilfe-Themen `nodes`/`jobs`.

## P6 — Imagebasierte Remote-VMs

**Commits:** `feat(node-agent): manage incus virtual machines`,
`feat(vms): route image vms to compute nodes`, `feat(vms): select target compute node`

### Node-Agent

- `_incus_vm.py`: allowlisteter VM-Lifecycle über `incus init --vm` mit explizitem
  Root-Disk, Ownership-Marker und hartem KVM-Capability-Gate; Netzwerk-Reconcile
  aus dem Container-Adapter wiederverwendet.
- ISO-Boot, Image-Import, Hostpfade und Passthrough sind über diesen Adapter
  nicht erreichbar.
- Resume-Guard erweitert: idempotente `vm.*`-Operationen dürfen bei Reconnect
  rekonziliieren, `vm.restart` bleibt fail-closed.

### Master

- Migration `047` ergänzt `vms.image` additiv (lokale VMs bleiben `NULL`).
- `vms/remote.py` und `vms/_remote_results.py`: transaktionale, generation-
  gebundene Job-Erzeugung und Resultprojektion (Spiegel von `containers.remote`).
- `vms/execution.py`: Dispatch lokal (QEMU) vs. remote (Incus) für den gesamten
  Lifecycle; Reconciler filtert Remote-VMs strikt.
- `job_protocol`, `_job_cancel`, `_job_leases` projizieren `vm.*`-Ergebnisse und
  -Fehler.
- Admin-only Remote-Create (Image-Pflicht, kein ISO/Import), kuratierte
  `GET /api/vms/quick-images`, Remote-Routing für start/stop/poweroff/delete.

### Frontend

- `CreateVMDialog` mit Ziel-Node-Auswahl (nur online + incus + kvm), kuratierter
  Image-Auswahl und Ausblenden der QEMU-spezifischen Felder auf Remote-Nodes.
- `VMCard` zeigt Remote-Node-Badge und Image; Stats-Polling überspringt Remote.

## P7 — Console-Tickets, Hardening und Abschluss

**Commits:** `feat(compute): issue resource-bound console tickets`,
`feat(node-agent): harden revocation and updates`

- Migration `048` `compute_console_tickets` (nur HMAC des Geheimnisses gespeichert).
- `compute/console_tickets.py`: kurzlebige (15–120 s), einmalige, ressourcen-
  gebundene Tickets; Ausgabe/Einlösung fail-closed; Remote-Ressourcen- und
  Online-Node-Gate; Node-Recheck bei Einlösung (Revocation-Race); Audit.
- Node-Widerruf invalidiert atomar alle offenen Tickets des Nodes.
- Admin-only `POST /api/compute/nodes/{id}/console-tickets`.
- `node-agent/update_manifest.py`: Ed25519-signiertes Update-Manifest + SHA-256/
  Größe + strikter Vorwärts-Versionscheck (Downgrade- und Tamper-Schutz).
- Härtungstests: Node claimt/liest nur eigene Jobs; widerrufener Node kann sich
  nicht authentisieren und keine Nachrichten senden.
- Betriebs-Runbook: `docs/compute-node-runbook.md` (Enrollment, Betrieb,
  Recovery, Widerruf, Deinstallation, Sicherheitsgrenzen).

## Verifikation

- **Backend (core):** 1861 pytest bestanden.
- **Node Agent:** 48 pytest bestanden.
- **Frontend:** `tsc` 0 Fehler, `vite build` grün, ESLint 0 Fehler.
- **Ruff:** `core/` und `node-agent/src` clean.
- **Security-Properties belegt:** Admin-Gates, keine Shell/feste argv, Update-
  Integrität (Signatur+Hash+Downgrade-Block), parametrisiertes SQL (nur feste
  Identifier), keine hardcodierten Secrets, coded errors ohne Detail-Leak.

## Noch nicht als reale Infrastruktur-Abnahme verifiziert (Rollout-Gate)

- Installer-Test auf frischem physischem Ubuntu-Node.
- Realer E2E-Test mit separatem Compute-Node (echter Incus-Daemon, `br0`, KVM).
- Mehrstündiger Netzpartition-/Reconnect- und Lasttest.

Diese Punkte sind keine versteckten Code-Todos, sondern das explizite physische
Rollout-Gate von V1.
