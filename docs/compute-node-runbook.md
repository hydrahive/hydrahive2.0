# HydraHive Compute Node — Betriebs-Runbook

**Stand:** 20. Juli 2026
**Gilt für:** Compute-Cluster V1 (P1–P7)
**Verbindliche Spezifikation:** [specs/compute-cluster-v1.md](specs/compute-cluster-v1.md)

Dieses Runbook beschreibt Installation, Betrieb, Recovery und Deinstallation eines
freigegebenen Ubuntu-Compute-Nodes. Der Node führt Remote-Container und
imagebasierte Remote-VMs über einen ausgehend verbundenen Node-Agent aus. Der
Agent nimmt keine eingehenden Verbindungen an und akzeptiert ausschließlich
signierte, allowlistete Incus-Operationen.

> **Rollout-Hinweis:** Der reale End-to-End-Test auf physischer Hardware ist ein
> ausdrückliches Rollout-Gate und kein Code-Todo. Dieses Runbook ist die
> Betriebsgrundlage dafür.

## 1. Voraussetzungen auf dem Node

- Ubuntu (LTS) mit installiertem und laufendem **Incus**; Bridge `br0` konfiguriert.
- Für VMs zusätzlich **KVM** (`/dev/kvm` lesbar/schreibbar für den Agent-Benutzer).
- Ausgehende HTTPS/WSS-Verbindung zum HydraHive-Master erlaubt.
- Python 3.12 für das `node-agent`-Paket.

Der Agent läuft als eigener Benutzer `hydrahive-node` mit ausschließlich den für
Incus notwendigen Gruppenrechten. Identität und Zustand liegen unter
`/var/lib/hydrahive-node/` mit restriktiven Dateirechten (`0600`/`0700`).

> **Einfachster Weg — geführtes Skript:** Auf dem neuen Node genügt
> `git clone …hydrahive2.0 && cd hydrahive2.0/node-agent && sudo sh scripts/setup.sh`.
> Das Skript prüft die Voraussetzungen, installiert den Agent und führt durch
> Kopplung + Freigabe. Vollständige Anleitung (inkl. der einmaligen Server-
> Vorbereitung mit Proxy/mTLS) in [`../node-agent/README.md`](../node-agent/README.md).
> Der Rest dieses Abschnitts beschreibt die manuellen Schritte, die das Skript
> automatisiert.

## 2. Node koppeln (Enrollment)

1. **Master (Admin, Cockpit → Admin → Compute-Nodes):** „Node koppeln" öffnen,
   eindeutigen Namen vergeben, Enrollment-Token erzeugen. Der Token ist einmalig
   und wird nur einmal angezeigt — sofort kopieren.
2. **Node:** Agent installieren und enrollen:
   ```bash
   # Token sicher übergeben (Datei mit 0600 oder via stdin):
   sudo -u hydrahive-node hydrahive-node enroll \
       --server https://<master-host> \
       --name compute-01 \
       --token-file /run/hydrahive-node-token \
       --ca-file /etc/hydrahive-node/server-ca.pem
   ```
   Der Agent generiert lokal ein Schlüsselpaar, sendet einen CSR und zeigt seinen
   **Zertifikat-Fingerprint** an.
3. **Master (Admin):** In der Node-Liste erscheint der Node als **Wartet**.
   „Freigeben" öffnen, den vom Agent gezeigten Fingerprint **exakt** vergleichen
   und bestätigen. Nur bei Übereinstimmung wird der Node freigegeben.
4. **Node:** Dienst starten:
   ```bash
   sudo systemctl enable --now hydrahive-node
   ```
   Der Node wird nach dem ersten Heartbeat **Online**.

## 3. Workloads platzieren

- **Remote-Container:** Container-Create-Dialog → Ziel-Node wählen (nur online +
  incus-fähig). Remote-Platzierung ist **Admin-only**. Der Container läuft
  dauerhaft auf dem gewählten Node (keine Migration in V1).
- **Remote-VMs:** VM-Create-Dialog → Ziel-Node wählen (nur online + incus + kvm).
  Auf Remote-Nodes werden **kuratierte Cloud-Images** angeboten; ISO-Boot, Import
  und Passthrough sind dort nicht verfügbar.
- Alle Mutationen (create/start/stop/restart/delete/inspect) laufen als
  persistente, signierte, node- und generation-gebundene Jobs. Der Fortschritt und
  strukturierte Fehler sind im Cockpit unter **Compute-Jobs** ohne Serverzugriff
  nachvollziehbar.

## 4. Laufender Betrieb

- **Heartbeats:** Der Agent sendet alle 30 s Heartbeat + Capability-/Ressourcen-
  Inventar. Ausbleibende Heartbeats → `offline`. Health-Warnungen → `degraded`.
- **Leeren (Drain):** Nimmt keine neuen Aktivierungsjobs mehr an; laufende
  Workloads bleiben, Stop/Delete/Inspect bleiben möglich. Für Wartung nutzen.
- **Deaktivieren:** Pausiert den Node vollständig (nimmt keine Jobs an).
- **Konsole:** Console-Zugriff läuft über kurzlebige, einmalige, ressourcen-
  gebundene Tickets (Admin-only, TTL 15–120 s). Ein Ticket autorisiert genau eine
  Session zu genau einer Ressource auf genau einem Node.

## 5. Recovery

### Agent-Neustart / Reboot des Nodes

- Der systemd-Dienst startet automatisch neu (`Restart=on-failure` + `enable`).
- Reconnect nutzt Backoff mit Jitter. Der Agent nimmt laufende Jobs nur über
  ACK-/Resume-Semantik wieder auf; **nicht-idempotente** Operationen
  (`vm.restart`, `container.restart`) werden bei unbekanntem Ausgang fail-closed
  nicht blind wiederholt.

### Master-seitige Job-Recovery

- Läuft eine Lease ab, wird ein `leased`-Job requeued und ein `running`-Job als
  `expired` terminal gesetzt; die Ressource erhält einen strukturierten
  Fehlerzustand (`lease_expired`).
- Bei Verbindungsabbruch während der Zustellung sichert der Agent Ergebnisse vor
  der Zustellung (write-before-deliver) und liefert sie idempotent nach.

### Node kurzzeitig offline

- Der Zustand bleibt konsistent; es werden keine neuen Aktivierungsjobs vergeben.
- Nach Rückkehr sendet der Agent wieder Heartbeats und der Node wird `online`.

### Agent-Update

- Updates werden **nur** mit signiertem Manifest (Ed25519, Master-Schlüssel) und
  geprüftem SHA-256 + Größe akzeptiert. Downgrades und manipulierte Artefakte
  werden abgelehnt (siehe `hydrahive_node.update_manifest`).

## 6. Widerruf (Revocation)

Ein kompromittierter oder ausgemusterter Node wird im Cockpit **widerrufen**:

1. Admin → Compute-Nodes → Node → „Widerrufen" (Bestätigung erforderlich).
2. Die Node-Identität wird **dauerhaft** ungültig. Der Agent kann sich nicht mehr
   verbinden (Auth schlägt fail-closed fehl).
3. Alle **offenen Console-Tickets** dieses Nodes werden im selben Vorgang
   invalidiert.
4. Ein widerrufener Node kann keine Jobs oder Secrets anderer Nodes lesen — jeder
   Node claimt und liest ausschließlich seine eigenen, node-gebundenen Jobs.

Widerruf ist nicht umkehrbar. Für erneute Nutzung muss der Host neu gekoppelt
werden (neuer Name/neue Identität).

## 7. Deinstallation

Auf dem **Master** zuerst widerrufen (Abschnitt 6), damit keine Reconnects mehr
möglich sind. Danach auf dem **Node**:

```bash
sudo systemctl disable --now hydrahive-node
sudo rm -rf /var/lib/hydrahive-node        # Identität + lokaler Job-Zustand
sudo rm -f  /etc/systemd/system/hydrahive-node.service
sudo systemctl daemon-reload
# Optional: Agent-Benutzer und -Paket entfernen
sudo userdel hydrahive-node
```

Von HydraHive erstellte Incus-Instanzen tragen den Ownership-Marker
`user.hydrahive.id`. Sie können nach dem Widerruf regulär über Incus entfernt
werden, falls sie nicht mehr gebraucht werden:

```bash
incus list -c n,user.hydrahive.id
incus delete <name> --force
```

## 8. Sicherheitsgrenzen (V1)

- Kein beliebiges Remote-Shell-Primitiv; nur allowlistete Incus-Operationen.
- Keine Host-Passthrough-Geräte oder freien Hostpfade für Remote-Workloads.
- Keine Live-Migration, kein automatisches Failover, kein automatischer Scheduler.
- Jeder Node hat eine eigene, widerrufbare Identität; TLS 1.3 mit Node-Bindung.
- Console-Tickets sind kurzlebig, einmalig und ressourcengebunden.
