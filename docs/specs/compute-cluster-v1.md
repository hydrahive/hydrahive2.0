# HydraHive Compute Cluster V1 — Node Agent + Incus

Status: **Design freigegeben**

Datum: 2026-07-19

## 1. Was

HydraHive wird um ein zentrales Compute-Control-Plane erweitert. Eine HydraHive-Hauptinstallation verwaltet mehrere Ubuntu-Server, auf denen ausschließlich ein schlanker HydraHive Node Agent und Incus laufen. Von der bestehenden HydraHive-Oberfläche aus können Administratoren Container und virtuelle Maschinen auf einem ausgewählten Compute-Node erstellen und verwalten.

V1 verwendet eine **manuelle Node-Auswahl** und eine **feste Platzierung**. Es gibt keine Live-Migration, kein automatisches Failover und keine automatische Lastverteilung.

## 2. Warum

Container und VMs werden heute implizit auf dem HydraHive-Host ausgeführt:

- Container über die lokale `incus`-CLI (`core/src/hydrahive/containers/incus_client.py`).
- VMs als lokale QEMU-Prozesse (`core/src/hydrahive/vms/lifecycle.py`).

Dadurch sind CPU, RAM und Storage an einen einzelnen Host gebunden. Compute-Nodes sollen zusätzliche Kapazität bereitstellen, ohne auf jedem Node eine vollständige HydraHive-Installation betreiben zu müssen.

## 3. Verbindliche Architekturentscheidungen

### 3.1 Control Plane und Worker

- Die bestehende HydraHive-Installation ist das einzige Control Plane.
- Worker sind normale Ubuntu-Server mit `hydrahive-node-agent` und Incus.
- Der Agent baut Verbindungen ausschließlich **ausgehend** zum Master auf.
- Auf Worker-Nodes wird keine HydraHive-Weboberfläche, keine LLM-Runtime und keine Projektdatenbank installiert.
- Der Master öffnet keine SSH-Sitzungen zu Nodes und führt dort keine freien Shell-Befehle aus.

### 3.2 Runtime

- Remote-Container laufen als Incus-Container.
- Remote-VMs laufen als Incus-VMs (`incus ... --vm`) mit KVM.
- Bestehende lokale Container bleiben über den bisherigen Incus-Pfad lauffähig.
- Bestehende lokale VMs bleiben in V1 über den bisherigen direkten QEMU-Pfad lauffähig.
- Der bestehende Host wird als reservierter Compute-Node `local` modelliert.

### 3.3 Platzierung

- Jede VM und jeder Container besitzt genau ein `node_id`.
- Bestehende Ressourcen werden auf `node_id='local'` migriert.
- Die Platzierung ändert sich in V1 nach der Erstellung nicht.
- Ein Node-Ausfall ändert den Ressourcenstatus nicht künstlich zu `stopped`; die UI zeigt zusätzlich den Node als `offline`.

### 3.4 V1-Grenze

V1 unterstützt keine:

- Live-Migration;
- automatische Neuplatzierung oder Hochverfügbarkeit;
- automatische Node-Auswahl;
- Shared-Storage-Orchestrierung;
- Ceph-Verwaltung;
- Cross-Node-Snapshots oder Backups;
- Remote-PCI-/USB-/Block-Device-Passthroughs;
- freie Remote-Shell;
- Docker-Socket-, libvirt- oder Incus-API-Freigabe im Netzwerk.

## 4. Komponenten

```text
┌─────────────────────────────────────────────────────┐
│ HydraHive Master                                    │
│                                                     │
│ Admin-UI · Node Registry · Job Queue · Audit · DB   │
└───────────────────────┬─────────────────────────────┘
                        │ ausgehender, gegenseitig
                        │ authentisierter Agentkanal
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Compute Node A │ │ Compute Node B │ │ Compute Node C │
│ Node Agent     │ │ Node Agent     │ │ Node Agent     │
│ Incus          │ │ Incus          │ │ Incus          │
│ Container/VMs  │ │ Container/VMs  │ │ Container/VMs  │
└────────────────┘ └────────────────┘ └────────────────┘
```

### 4.1 Master

Der Master stellt bereit:

- Admin-only Node-Registry;
- Enrollment-Tokens und Zertifikatsausstellung;
- Node-Freigabe, Sperrung und Widerruf;
- Heartbeat-/Capability-Verarbeitung;
- persistente Compute-Jobs mit Lease und Idempotenz;
- typisierte Command-Erzeugung;
- Agent-Protokoll und Versionsaushandlung;
- Ressourcen-/Node-Zuordnung;
- Audit-Events;
- später einen autorisierten Console-Proxy.

### 4.2 Node Agent

Der Node Agent ist ein separates, minimales Python-Paket im Repository unter `node-agent/`. Er wird als systemd-Dienst betrieben und enthält keine HydraHive-LLM- oder Frontend-Abhängigkeiten.

Aufgaben:

- Enrollment und lokale Schlüsselgenerierung;
- ausgehender Agentkanal;
- Heartbeats und Capability-Inventar;
- atomarer Claim genau eines passenden Jobs;
- Ausführung ausschließlich allowlisteter Incus-Operationen;
- Fortschritt und strukturierte Resultate;
- idempotente Wiederaufnahme nach Reconnect;
- lokale Parallelitäts- und Ressourcenlimits;
- sichere Agent-Aktualisierung in einer späteren V1-Etappe.

Der Dienst läuft als eigener Benutzer `hydrahive-node`, erhält ausschließlich die für Incus notwendigen Gruppenrechte und speichert Identität unter `/var/lib/hydrahive-node/` mit restriktiven Dateirechten.

## 5. Datenmodell

Neue additive Migrationsserie: `032_compute_nodes.sql` bis `039_compute_placement_integrity.sql`. Die Registry-/Jobtabellen sind idempotent; jede Legacy-Tabellenerweiterung liegt in einer eigenen Migration, damit ein Teilfehler sicher wiederaufgenommen werden kann.

### 5.1 `compute_nodes`

- `node_id TEXT PRIMARY KEY`
- `name TEXT NOT NULL UNIQUE`
- `kind TEXT NOT NULL` — `local|agent`
- `status TEXT NOT NULL` — `pending|online|degraded|offline|draining|disabled|revoked`
- `certificate_fingerprint TEXT UNIQUE`
- `protocol_version INTEGER NOT NULL`
- `agent_version TEXT`
- `capabilities_json TEXT NOT NULL`
- `resources_json TEXT NOT NULL`
- `labels_json TEXT NOT NULL`
- `last_seen_at TEXT`
- `approved_at TEXT`
- `approved_by TEXT`
- `revoked_at TEXT`
- `created_at TEXT NOT NULL`
- `updated_at TEXT NOT NULL`

Die Migration legt den reservierten Node an:

```text
node_id = local
name = Local Host
kind = local
status = online
```

### 5.2 `compute_enrollment_tokens`

- `token_id TEXT PRIMARY KEY`
- `token_hmac TEXT NOT NULL UNIQUE`
- `requested_name TEXT NOT NULL`
- `expires_at TEXT NOT NULL`
- `consumed_at TEXT`
- `created_by TEXT NOT NULL`
- `created_at TEXT NOT NULL`

Es wird ausschließlich ein HMAC gespeichert. Token: mindestens 256 Bit Entropie, zehn Minuten TTL, einmaliger Verbrauch, Rate-Limit.

### 5.3 `compute_jobs`

- `job_id TEXT PRIMARY KEY`
- `node_id TEXT NOT NULL`
- `resource_kind TEXT NOT NULL` — `container|vm|node`
- `resource_id TEXT`
- `operation TEXT NOT NULL`
- `generation INTEGER NOT NULL`
- `payload_json TEXT NOT NULL`
- `idempotency_key TEXT NOT NULL UNIQUE`
- `status TEXT NOT NULL` — `queued|leased|running|succeeded|failed|cancelled|expired`
- `lease_id TEXT`
- `lease_until TEXT`
- `attempts INTEGER NOT NULL DEFAULT 0`
- `progress INTEGER NOT NULL DEFAULT 0`
- `error_code TEXT`
- `error_params_json TEXT`
- `created_by TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `started_at TEXT`
- `finished_at TEXT`

### 5.4 `compute_job_events`

Append-only Fortschritts- und Auditverlauf:

- `event_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `job_id TEXT NOT NULL`
- `sequence INTEGER NOT NULL`
- `event_type TEXT NOT NULL`
- `data_json TEXT NOT NULL`
- `created_at TEXT NOT NULL`
- `UNIQUE(job_id, sequence)`

### 5.5 Bestehende Ressourcen

Additiv:

- `containers.node_id TEXT NOT NULL DEFAULT 'local'`
- `containers.generation INTEGER NOT NULL DEFAULT 0`
- `vms.node_id TEXT NOT NULL DEFAULT 'local'`
- `vms.generation INTEGER NOT NULL DEFAULT 0`
- `vms.runtime TEXT NOT NULL DEFAULT 'qemu'` — `qemu|incus`
- `vms.runtime_ref TEXT`

Bestehende lokale VMs bleiben `runtime='qemu'`. Neue Agent-VMs erhalten `runtime='incus'` und einen node-lokalen, serverseitig erzeugten `runtime_ref`.

## 6. Agent-Protokoll

### 6.1 Enrollment

1. Admin erzeugt in HydraHive einen kurzlebigen Enrollment-Token für einen Node-Namen.
2. Agent erzeugt lokal privaten Schlüssel und CSR.
3. Agent sendet Token, CSR, Agent-/Protokollversion und initiale Capabilities über den normalen serverauthentisierten HTTPS-Endpunkt.
4. Master verbraucht den Token atomar, stellt ein individuelles Clientzertifikat aus und registriert den Node als `pending`.
5. CLI und UI zeigen denselben Zertifikatsfingerprint.
6. Admin bestätigt den Fingerprint und aktiviert den Node.
7. Erst danach werden Heartbeats und Jobs akzeptiert.

### 6.2 Laufender Kanal

- TLS 1.3 mit individueller Node-Identität; Reverse Proxy und Backend müssen die verifizierte Clientidentität fail-closed an den Agent-Endpunkt binden.
- Protokollnachrichten sind streng typisiert und versionsgebunden.
- Jede Nachricht enthält Node-ID, Sequenz, Zeitfenster und Nonce.
- Der Master signiert kanonische Jobs; der Agent kennt nur den öffentlichen Job-Signaturschlüssel.
- Der Agent darf ausschließlich Jobs für seine eigene Node-ID claimen.
- Reconnect verwendet ACK-/Resume-Semantik; Jobs werden nicht allein wegen eines Verbindungsabbruchs erneut ausgeführt.

V1-Nachrichtentypen:

- `hello`
- `heartbeat`
- `capabilities`
- `job_offer`
- `job_accept`
- `job_started`
- `job_progress`
- `job_succeeded`
- `job_failed`
- `job_cancelled`
- `ack`

### 6.3 Job-Lease und Idempotenz

- Claim erfolgt atomar mit eindeutiger `lease_id` und Ablaufzeit.
- Agent persistiert zuletzt verarbeitete Idempotency-Keys lokal.
- Ein Job enthält Node-ID, Ressource, Generation, Ablaufzeit und Signatur.
- Veraltete Generationen und abgelaufene Jobs werden abgelehnt.
- Wiederholte Resultate sind serverseitig idempotent.
- Nach Lease-Ablauf entscheidet der Master anhand des Agentstatus über erneutes Leasing; laufende create/delete-Operationen werden nicht blind doppelt gestartet.

## 7. Erlaubte Operationen

Keine Operation enthält freie Shell-Befehle. V1-Allowlist:

### Container

- `container.create`
- `container.start`
- `container.stop`
- `container.restart`
- `container.delete`
- `container.inspect`

### VM

- `vm.create_from_image`
- `vm.start`
- `vm.stop`
- `vm.restart`
- `vm.delete`
- `vm.inspect`

V1-Remote-VMs werden ausschließlich aus kuratierten Incus-Images erstellt. ISO-Upload, Disk-Import, Passthrough und direkte Hostpfade bleiben auf `local` begrenzt.

## 8. Capabilities und Ressourcen

Ein Agent meldet unter anderem:

- Hostname und Betriebssystem;
- Agent-, Incus- und Protokollversion;
- Architektur;
- CPU-Kerne und aktuelle Auslastung;
- RAM gesamt/verfügbar;
- Storage-Pools und freie Bytes;
- KVM-Verfügbarkeit;
- unterstützte Instanztypen;
- verfügbare Netzwerkprofile;
- Health-Fehler.

Diese Angaben dienen in V1 zur Validierung und Anzeige, nicht zur automatischen Platzierung.

## 9. API

Admin-/User-API über bestehende HydraHive-Authentifizierung:

- `GET /api/compute/nodes`
- `GET /api/compute/nodes/{node_id}`
- `POST /api/compute/enrollments`
- `POST /api/compute/nodes/{node_id}/approve`
- `POST /api/compute/nodes/{node_id}/drain`
- `POST /api/compute/nodes/{node_id}/enable`
- `DELETE /api/compute/nodes/{node_id}` — Widerruf, keine implizite Workload-Löschung
- `GET /api/compute/jobs`
- `GET /api/compute/jobs/{job_id}`
- `POST /api/compute/jobs/{job_id}/cancel`

Öffentlicher, tokenautorisierter Bootstrap-Endpunkt:

- `POST /api/compute/agent/enroll`

Agent-Endpunkt mit Node-Identität:

- `WSS /api/compute/agent/connect`

Bestehende Create-Payloads erhalten `node_id`. Ohne Angabe wird aus Kompatibilitätsgründen `local` verwendet.

## 10. UI

### 10.1 Compute-Nodes

Neuer admin-only Cockpit-Bereich:

- `/admin?section=nodes`
- `/admin?section=nodes&node=<id>`
- `/admin?section=jobs`

Node-Karte und Detail zeigen:

- Status und letzte Verbindung;
- CPU, RAM und Storage;
- Agent-/Incus-Version;
- KVM- und Container-Capability;
- Anzahl zugeordneter VMs/Container;
- Wartungsmodus;
- letzte Jobs und strukturierte Fehler;
- Approve, Drain, Disable und Revoke.

### 10.2 Create-Dialoge

`CreateContainerDialog` und `CreateVMDialog` erhalten eine Node-Auswahl.

- Default ist `local`.
- Nur online Nodes mit passender Capability sind auswählbar.
- Offline/ungeeignete Nodes bleiben sichtbar, aber deaktiviert und begründet.
- V1 enthält keine Option „automatisch auswählen“.
- Remote-VM-Dialog bietet nur Image-basierte Erstellung; ISO, Import und Passthrough werden deaktiviert und erklärt.

### 10.3 Ressourcenstatus

Container- und VM-Karten zeigen zusätzlich Node-Name und Node-Status. Ein offline Node überlagert die Erreichbarkeit, überschreibt aber nicht den zuletzt bekannten Instanzstatus.

## 11. Sicherheitsanforderungen

### Critical

- Individuelle Node-Identität, kein Shared Cluster Secret.
- Einmaliger Enrollment-Token mit HMAC-at-rest, TTL und Rate-Limit.
- Gegenseitig authentisierter, fail-closed Agentkanal.
- Kein beliebiger Shell-, Pfad- oder Argument-Input.
- Jobs sind signiert, nodegebunden, zeitbegrenzt, generationsgebunden und idempotent.
- Secrets erscheinen nie in URL, Kommandozeile, Logs, Events oder Jobresultaten.
- Keine direkten VNC-, TTY-, Incus-, Docker- oder libvirt-Ports.
- Widerruf trennt aktive Agent-/Console-Kanäle und verhindert Reconnect.
- Agent-Updates werden nur mit signiertem Manifest und geprüftem Hash akzeptiert.

### High

- Admin-Freigabe mit sichtbarem Fingerprint.
- Audit für Enrollment, Approve, Revocation und jeden Jobzustandswechsel.
- Heartbeat, Dead-Detection und Reconnect mit Jitter.
- Leases, Timeouts, Parallelitäts- und Outputlimits.
- Ein kompromittierter Node kann keine Jobs oder Secrets anderer Nodes lesen.
- Console-Tickets sind kurzlebig, einmalig und ressourcengebunden.

## 12. Fehler- und Offline-Semantik

- `offline`: Heartbeat-Frist überschritten; keine neuen Jobs.
- `degraded`: Agent erreichbar, aber Capability-/Storage-/Incus-Health eingeschränkt.
- `draining`: keine neuen Creates; Lifecycle bestehender Ressourcen bleibt möglich.
- `disabled`: keine neuen Jobs; bestehende Verbindung wird kontrolliert abgewiesen.
- `revoked`: Zertifikat gesperrt, aktive Kanäle getrennt, keine Reaktivierung ohne neues Enrollment.

Master-Ausfall stoppt keine laufenden Workloads. Der Agent startet während eines Master-Ausfalls keine neuen Jobs und führt nur bereits eindeutig akzeptierte Operationen zu Ende.

## 13. Rollout und Rückwärtskompatibilität

1. Migration legt `local` an und backfillt alle Ressourcen.
2. Bestehende Container-/VM-Endpunkte verhalten sich ohne `node_id` unverändert lokal.
3. Node-Registry und read-only Heartbeats werden zuerst ausgeliefert.
4. Remote-Container werden vor Remote-VMs aktiviert.
5. Remote-VMs sind zunächst ausschließlich imagebasiert.
6. Legacy-QEMU-VMs werden in V1 nicht automatisch konvertiert.

## 14. Akzeptanzkriterien V1

- Ein Ubuntu-Node kann mit einem einmaligen Token registriert und durch einen Admin freigegeben werden.
- Der Agent benötigt keinen eingehenden Verwaltungsport.
- HydraHive zeigt Node-Status, Ressourcen und Capabilities korrekt an.
- Ein Administrator kann beim Erstellen eines Containers oder einer imagebasierten VM einen online Node auswählen.
- Jobs sind persistent, idempotent, abbrechbar und nach Reconnect nachvollziehbar.
- Container und VMs lassen sich remote erstellen, starten, stoppen, neu starten, inspizieren und löschen.
- Ein offline Node erhält keine neuen Jobs und verändert nicht den zuletzt bekannten Instanzstatus.
- Bestehende lokale Container und QEMU-VMs funktionieren unverändert weiter.
- Ein widerrufener Node kann sich nicht erneut verbinden oder Jobs claimen.
- Kein Agent-Endpunkt akzeptiert freie Shell-Befehle.
- Audit, Backendtests, Agenttests und Frontend-Build sind grün.
