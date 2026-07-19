# HydraHive Node Agent

Der Node Agent ist ein eigenständiges, minimales Python-Paket, das einen
freigegebenen Ubuntu-Host zu einem HydraHive-**Compute-Node** macht. Er verbindet
sich **ausgehend** mit dem HydraHive-Master, sendet Heartbeats und führt
ausschließlich signierte, allowlistete Incus-Operationen aus (Remote-Container und
imagebasierte Remote-VMs). Der Agent nimmt **keine** eingehenden Verbindungen an
und kennt keine LLM- oder Frontend-Abhängigkeiten.

- Vollständiges Betriebs-Runbook: [`../docs/compute-node-runbook.md`](../docs/compute-node-runbook.md)
- Architektur/Spec: [`../docs/specs/compute-cluster-v1.md`](../docs/specs/compute-cluster-v1.md)

---

## 1. Woher bekomme ich den Node-Client?

Der Agent-Code liegt in **diesem Repository** unter `node-agent/`. Es gibt kein
separates Download-Paket — du bringst den Ordner auf den Zielhost und installierst
ihn dort. Drei übliche Wege:

**A) Repo direkt auf dem Node klonen (einfachster Weg)**
```bash
git clone https://github.com/hydrahive/hydrahive2.0.git
cd hydrahive2.0/node-agent
```

**B) Nur den node-agent-Ordner per rsync/scp auf den Node kopieren**
```bash
# vom Master/Arbeitsrechner aus:
rsync -a node-agent/ root@<node-host>:/opt/hydrahive-node-agent/
# --exclude '.venv' --exclude '.pytest_cache' schadet nicht
```

**C) Als Wheel bauen und übertragen**
```bash
cd node-agent
python3 -m pip install build && python3 -m build   # erzeugt dist/hydrahive_node_agent-*.whl
scp dist/*.whl root@<node-host>:/tmp/
# auf dem Node:  pip install /tmp/hydrahive_node_agent-*.whl
```

Der Agent hat nur drei Laufzeit-Abhängigkeiten (`cryptography`, `httpx`,
`websockets`) und braucht Python ≥ 3.12.

---

## 2. Voraussetzungen auf dem Node

- **Ubuntu** (LTS empfohlen) mit Root-/sudo-Zugriff.
- **Incus** installiert und initialisiert, Bridge **`br0`** vorhanden
  (`incus network list`). Die Gruppe `incus-admin` muss existieren.
- Für **VMs** zusätzlich **KVM**: `/dev/kvm` vorhanden und für den Agent-Benutzer
  les-/schreibbar (`ls -l /dev/kvm`).
- **Ausgehende HTTPS/WSS-Verbindung** zum Master erlaubt (kein eingehender Port
  nötig).
- Python ≥ 3.12.

> Incus zuerst einrichten. Ohne die Gruppe `incus-admin` bricht der Installer
> bewusst ab.

---

## 3. Master-seitige Vorbereitung (einmalig)

Der Agentkanal ist mTLS-gesichert: Der Agent authentisiert sich mit einem
Client-Zertifikat, das die HydraHive-**Compute-CA** ausgestellt hat. Ein
Reverse-Proxy vor dem Master terminiert TLS, prüft das Client-Zertifikat und
reicht Identität + ein gemeinsames Proxy-Secret als Header an das Backend weiter.

### 3.1 Proxy-Secret setzen

Das Backend akzeptiert Agent-Verbindungen nur, wenn der Proxy ein passendes
Secret mitschickt (`HH_COMPUTE_PROXY_SECRET`). In der Master-Umgebung setzen
(z. B. `/etc/hydrahive2/env`):

```
HH_COMPUTE_PROXY_SECRET=<langes-zufälliges-secret>
```

Danach den HydraHive-Dienst neu starten.

### 3.2 Compute-CA

Die Compute-CA wird **automatisch** beim ersten Enrollment erzeugt und unter
`HH_COMPUTE_PKI_DIR` (Default `<config>/compute-pki/`) abgelegt:
`ca-cert.pem` (öffentlich) und `ca-key.pem` (geheim, `0600`). Das
`ca-cert.pem` brauchst du im Reverse-Proxy für `ssl_verify_client` sowie
optional auf dem Node als `--ca-file`.

### 3.3 Reverse-Proxy (Beispiel nginx)

```nginx
# WSS-Endpunkt ausschließlich für Compute-Agents
location /api/compute/agent/connect {
    # Client-Zertifikat gegen die Compute-CA verifizieren
    ssl_verify_client       on;
    ssl_client_certificate  /etc/hydrahive2/compute-pki/ca-cert.pem;

    # Verifizierte Identität + Proxy-Secret ans Backend weiterreichen
    proxy_set_header X-HydraHive-Client-Cert   $ssl_client_escaped_cert;
    proxy_set_header X-HydraHive-Proxy-Secret  "<dasselbe-secret-wie-HH_COMPUTE_PROXY_SECRET>";
    proxy_set_header X-HydraHive-Node-ID       $http_x_hydrahive_node_id;

    # WebSocket-Upgrade
    proxy_http_version 1.1;
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_pass http://127.0.0.1:8001;
}
```

> Das Backend prüft fail-closed: ohne gültiges, von der Compute-CA signiertes
> Client-Zertifikat **und** korrektes Proxy-Secret wird die Verbindung mit
> `4403 agent_identity_invalid` abgewiesen. Ein widerrufener Node kann sich nicht
> mehr verbinden.

---

## 4. Agent installieren

Auf dem Node als root im `node-agent`-Ordner:

```bash
sudo ./scripts/install.sh
```

Der Installer:
- legt System-Benutzer/-Gruppe `hydrahive-node` an (Login gesperrt),
- fügt ihn der Gruppe `incus-admin` hinzu,
- erstellt `/var/lib/hydrahive-node/` (`0700`),
- installiert das Paket (`pip install .`) → CLI `hydrahive-node`,
- installiert die gehärtete systemd-Unit und aktiviert sie (startet aber noch
  nicht).

---

## 5. Node koppeln (Enrollment)

**Schritt 1 — Master (Admin):** Cockpit → **Admin → Compute-Nodes → „Node
koppeln"**. Eindeutigen Namen vergeben, **Enrollment-Token** erzeugen. Der Token
ist einmalig und wird nur einmal angezeigt → sofort kopieren.

**Schritt 2 — Node:** Enrollment ausführen. Den Token sicher übergeben (Datei mit
`0600` oder via stdin, nicht als Klartext-Argument):

```bash
# Token in eine 0600-Datei legen und referenzieren:
umask 077; printf '%s' '<TOKEN>' > /run/hh-node-token
sudo -u hydrahive-node hydrahive-node enroll \
    --server https://<master-host> \
    --name  <exakt-der-name-aus-schritt-1> \
    --token-file /run/hh-node-token \
    --ca-file /etc/hydrahive2/compute-pki/ca-cert.pem   # optional, empfohlen
rm -f /run/hh-node-token
```

Alternativen zur Token-Übergabe: `--token-stdin` (Token über die Standardeingabe)
oder ganz ohne Flag → interaktive Passwort-Abfrage.

Der Agent generiert lokal ein Schlüsselpaar, sendet einen CSR und gibt aus:
```
Node ID: <node-id>
Certificate fingerprint: <sha256-fingerprint>
```

**Schritt 3 — Master (Admin):** In der Node-Liste erscheint der Node als
**„Wartet"**. **„Freigeben"** öffnen, den vom Agent gezeigten **Fingerprint exakt
vergleichen** und bestätigen. Nur bei Übereinstimmung wird der Node freigegeben.

**Schritt 4 — Node:** Dienst starten:
```bash
sudo systemctl enable --now hydrahive-node
sudo systemctl status hydrahive-node
```
Nach dem ersten Heartbeat wird der Node im Cockpit **Online**.

---

## 6. Workloads platzieren

- **Remote-Container:** Container-Create-Dialog → Ziel-Node wählen (nur online +
  incus-fähig; Admin-only). Die Container-Karte zeigt ein Remote-Node-Badge.
- **Remote-VMs:** VM-Create-Dialog → Ziel-Node wählen (nur online + incus + kvm).
  Auf Remote-Nodes werden kuratierte Cloud-Images angeboten; ISO-Boot, Import und
  Passthrough sind dort nicht verfügbar.

Alle Mutationen laufen als persistente, node- und generation-gebundene Jobs und
sind im Cockpit unter **Compute-Jobs** mit Event-Timeline nachvollziehbar.

---

## 7. Troubleshooting

| Symptom | Ursache / Prüfung |
|---|---|
| `incus-admin group is missing` beim Install | Incus nicht installiert/initialisiert. Erst `incus admin init`. |
| Enrollment `enrollment request failed` | Server-URL falsch/nicht per HTTPS erreichbar, oder Token abgelaufen (TTL) / schon verbraucht. Neuen Token erzeugen. |
| Enrollment `fingerprint mismatch` / `certificate does not match` | Manipulierte oder falsche Antwort. Enrollment abbrechen, `--ca-file` prüfen. |
| Node bleibt **Wartet** | Fingerprint im Cockpit noch nicht freigegeben (Schritt 3). |
| WS schließt mit `4403 agent_identity_invalid` | Reverse-Proxy reicht Client-Cert/Proxy-Secret nicht korrekt weiter, `HH_COMPUTE_PROXY_SECRET` stimmt nicht, oder Node wurde widerrufen. |
| Node wird **degraded** | Health-Warnung im Heartbeat (z. B. Incus-Socket nicht erreichbar). `journalctl -u hydrahive-node` prüfen. |
| VMs nicht wählbar | `/dev/kvm` fehlt oder ohne Rechte → Node meldet keine `kvm`-Capability. |

Logs des Agents:
```bash
sudo journalctl -u hydrahive-node -f
```

---

## 8. Widerruf & Deinstallation

**Master zuerst:** Admin → Compute-Nodes → Node → **„Widerrufen"** (Bestätigung).
Das macht die Node-Identität dauerhaft ungültig und invalidiert alle offenen
Console-Tickets. Danach auf dem **Node**:

```bash
sudo systemctl disable --now hydrahive-node
sudo rm -rf /var/lib/hydrahive-node
sudo rm -f  /etc/systemd/system/hydrahive-node.service
sudo systemctl daemon-reload
sudo userdel hydrahive-node        # optional
```

Von HydraHive erstellte Incus-Instanzen tragen den Marker `user.hydrahive.id` und
können regulär über Incus entfernt werden:
```bash
incus list -c n,user.hydrahive.id
incus delete <name> --force
```

---

## 9. Entwicklung / Tests

```bash
cd node-agent
python3 -m venv .venv && . .venv/bin/activate
pip install -e . pytest
PYTHONPATH="$PWD/src" pytest -q
```
