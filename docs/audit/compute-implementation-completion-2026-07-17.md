# Compute-Implementierungsabschluss P1–P4

**Datum:** 17. Juli 2026
**Branch:** `feat/remote-containers`
**Umfang:** Compute-Cluster-Grundlage bis Remote-Container-Routing

## Kurzfazit

Die Phasen P1 bis P4 der Compute-Cluster-V1-Planung sind im Code umgesetzt. HydraHive besitzt jetzt ein additives Node-/Job-Datenmodell, sicheres Enrollment, einen ausgehend verbundenen Node Agent, persistente signierte Compute-Jobs und ein vollständiges Remote-Container-Routing. Bestehende lokale Container bleiben auf ihrem bisherigen Incus-Lifecycle-Pfad; lokale QEMU-VMs wurden nicht auf den Agentpfad umgestellt.

Die automatisierten Core- und Agenttests sind grün. Ein Rollout auf einen physischen, separat betriebenen Ubuntu-/Incus-Node ist noch kein Bestandteil dieser Code-Abnahme und bleibt ein ausdrückliches P7-Rollout-Gate.

## P1 — Compute-Node-Datenmodell und lokale Kompatibilität

**PR/Integration:** Foundation-PRs bis `c2baa2fe`
**Relevante Commits:** `7608a337`, `ccd04dbe`

Umgesetzt:

- additive Compute-Migrationen mit Node-, Enrollment-, Job- und Eventtabellen;
- reservierter lokaler Node;
- parametrisierte Node-Registry und kontrollierte Statusübergänge;
- `node_id` und `generation` für Container und VMs;
- Default `node_id=local` für bestehende API-Payloads;
- lokale Reconciler und Runtime-Pfade sind gegen Remote-Ressourcen abgegrenzt;
- Placement- und Referential-Integrity-Regeln.

Ergebnis: Bestehende Installationen können das Schema additiv übernehmen; lokale Workloads behalten ihr Verhalten.

## P2 — Enrollment, Identität und Agentkanal

**Merge:** `df0ae4a8` / PR #363
**Relevante Commits:** `f31bf7ae`, `8afe7768`, `eda8f561`, `79799940`

Umgesetzt:

- 256-Bit-Enrollment-Tokens mit HMAC-at-rest, TTL und Einmalverbrauch;
- Compute-CA und signierte Node-Zertifikate;
- CSR-/Fingerprint-Prüfung und Admin-Freigabe;
- Disable-/Revoke-Pfade;
- separates `node-agent`-Paket mit Enrollment- und Run-CLI;
- restriktive State-Dateirechte und systemd-Härtung;
- ausgehender mTLS-WebSocket-Kanal;
- versionierte Nachrichten, Sequenz-/Nonce-Prüfung und Node-Bindung;
- Heartbeats, Ressourcen- und Capability-Inventar;
- Online-/Degraded-/Offline-Erkennung.

Ergebnis: Ein Node kann gekoppelt, freigegeben, überwacht und widerrufen werden, ohne eingehenden Agent-Port.

## P3 — Persistente Compute-Jobs

**Merge:** `d790a9ed` / PR #364
**Relevante Commits:** `3cc1ee40`, `fc628ef4`, `d351d287`, `9914b89e`

Umgesetzt:

- persistente Jobzustandsmaschine und Eventtimeline;
- atomarer nodegebundener Claim;
- Lease, Renewal, Expiry, Cancel und Fortschritt;
- Ed25519-signierte Jobangebote;
- strikte Operation-Allowlist und fail-closed Dispatcher;
- agentseitige Write-before-execute-/Write-before-deliver-Journale;
- Idempotency-Key und Reconnect-Recovery;
- sichere Behandlung nicht rekonstruierbarer Operationsausgänge;
- Admin-/Owner-Job-API mit begrenzten Resultaten;
- strukturierte Fehlercodes ohne rohe Prozessausgabe.

Ergebnis: Jobs und Resultate überstehen Verbindungsabbrüche, ohne eine nicht idempotente Operation blind zu wiederholen.

## P4 — Remote-Container End-to-End

**Commits:** `cadf53dd`, `c35e5a70`

### Agentseitiger Incus-Adapter

- fester Incus-Pfad `/usr/bin/incus`;
- `asyncio.create_subprocess_exec` ohne Shell;
- strikte Validierung von Name, Image, Ressourcen, Netzwerk und Resource-ID;
- Ownership-Marker `user.hydrahive.id` vor jeder Lifecycle-Mutation;
- unprivilegierte Container ohne pauschales Nesting;
- Create über `incus init`, anschließend verifizierte Netzwerkkonfiguration, danach Start;
- `isolated` überschreibt geerbtes `eth0` mit `type=none`;
- `bridged` bindet `eth0` an `br0`;
- idempotente Netzwerkpfade `override → set → add` mit Postcondition-Prüfung;
- Output-, Timeout- und Parallelitätsgrenzen;
- Timeout-Reconciliation für Create/Start/Stop/Delete und Netzwerk;
- Crash-Reconciliation nur für idempotente Operationen; Restart bleibt bei unbekanntem Ausgang fail-closed;
- Resume erneuert die bestehende Lease vor jeder Runtime-Mutation;
- Agent-Heartbeat und Jobloop laufen parallel;
- Installer bindet den dedizierten Agentbenutzer an die notwendige Incus-Administrationsgruppe des Compute-Nodes.

### Masterseitiges Routing

- gemeinsamer Execution-Adapter hält Local und Remote explizit getrennt;
- Remote-Placement ist Admin-only;
- Create/Start/Stop/Restart/Delete/Inspect werden als generationgebundene Jobs geroutet;
- Container-State-Transition und Job-Insert sind atomar und CAS-geschützt;
- Jobabschluss und Containerprojektion laufen in derselben Transaktion;
- Resultprojektion prüft Node und Generation;
- ungültige Success-Resultate werden als `failed/agent_result_invalid` gespeichert;
- Cancel und Running-Lease-Expiry projizieren strukturierte Containerfehler;
- Draining-Nodes nehmen nur Stop/Delete/Inspect an und leasen keine Aktivierungsjobs;
- Remote-Info ist ein read-only Cache-Read;
- expliziter Remote-Refresh läuft über `POST /api/containers/{id}/refresh` mit dedupliziertem Inspect-Job;
- Local-Container verwenden unverändert den bestehenden Lifecycle.

## Verifikation

### P4 fokussiert

- Core: **50 Tests bestanden**.
- Node Agent: **26 Tests bestanden**.
- Ruff für alle geänderten Core-/Agentmodule und Tests: bestanden.
- Shellsyntax des Agentinstallers: bestanden.
- Security-Reviews für Agent und Core: keine offenen Blocker, High- oder Medium-Funde nach Nachbesserungen.

Abgedeckte kritische Fälle:

- Flag-/Payload-Injection und fremde Incus-Ownership;
- Netzwerk-Isolation vor dem ersten Start;
- Netzwerk-Fallbacks und Timeout-Reconciliation;
- Wiederaufnahme nur mit gültiger Lease;
- Admin-only Remote-Placement;
- Offline-/Draining-Policy;
- Rollback bei Job-Insert- oder Resultprojektionsfehlern;
- stale Generation und ungültige Agentresultate;
- Cancel-/Lease-Expiry-Projektion;
- lokale Routing-Guards.

## Noch nicht als reale Infrastruktur-Abnahme verifiziert

- Installation auf einem frischen physischen Ubuntu-Host;
- Kommunikation mit einem echten Incus-Daemon und realem `br0`;
- längerer Netzpartition-/Reconnect-Test über mehrere Stunden;
- Lasttest mit vielen parallelen Nodes und Workloads;
- Upgrade eines bereits produktiven Node Agents;
- P5-Cockpit-UX, P6-Remote-VMs und P7-Console-Proxy.

Diese Punkte sind keine versteckten P4-Code-Todos, sondern explizite Rollout- beziehungsweise Folgephasen-Gates.
