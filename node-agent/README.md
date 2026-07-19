# HydraHive Compute-Node

Mit einem Compute-Node hängst du einen weiteren Rechner (Ubuntu-Server) an
HydraHive an, damit dort Container und virtuelle Maschinen laufen. Der Node
verbindet sich von selbst nach außen zum HydraHive-Server — du musst am Node
**keine Ports öffnen** und keine Firewall umbauen.

---

## Schnellstart — einen Node dazuhängen (für alle)

> Das ist der normale Fall: Du hast einen fertigen HydraHive-Server und willst
> einen weiteren Rechner als Compute-Node dazunehmen. Voraussetzung: Auf dem
> Server hat der Admin die **einmalige Einrichtung** (ganz unten) schon gemacht.

Du brauchst nur ein Terminal auf dem neuen Rechner. Kopiere diese Befehle:

```bash
# 1. HydraHive-Projekt holen (falls noch nicht da)
git clone https://github.com/hydrahive/hydrahive2.0.git
cd hydrahive2.0/node-agent

# 2. Geführte Einrichtung starten
sudo sh scripts/setup.sh
```

Das Skript nimmt dich an die Hand und fragt der Reihe nach:

1. **Prüft**, ob Incus (und optional KVM für VMs) vorhanden ist.
2. **Installiert** den Node-Agent.
3. **Fragt** nach der Server-Adresse, einem Namen für den Node und dem
   **Kopplungs-Code**. Den Code holst du im Browser aus dem Cockpit:
   **Admin → Compute-Nodes → „Node koppeln"** → Namen vergeben → Token kopieren.
4. **Koppelt** den Node und zeigt dir einen **Sicherheits-Code**.
5. Du klickst im Cockpit auf **„Freigeben"** und vergleichst den Sicherheits-Code.
   Dann drückst du Enter — fertig. Der Node erscheint als **„Online"**.

Danach kannst du beim Anlegen von Containern und VMs diesen Node auswählen.

**Wenn etwas schiefgeht**, sagt dir das Skript im Klartext, was zu tun ist. Log
ansehen:
```bash
journalctl -u hydrahive-node -f
```

Node später wieder entfernen: im Cockpit **„Widerrufen"**, dann auf dem Node:
```bash
sudo systemctl disable --now hydrahive-node
sudo rm -rf /var/lib/hydrahive-node
```

Das war's für den Normalfall. Alles darunter ist Hintergrundwissen und die
einmalige Server-Einrichtung für Admins.

---

## Voraussetzungen am Node

- **Ubuntu** (LTS empfohlen) mit sudo-Zugriff.
- **Incus** installiert und initialisiert (`incus admin init`), Bridge **`br0`**.
  Das Setup-Skript prüft das und sagt dir, falls etwas fehlt.
- Für **virtuelle Maschinen** zusätzlich **KVM** (`/dev/kvm`). Fehlt es, läuft der
  Node trotzdem — dann eben nur mit Containern.
- Python ≥ 3.12 (auf aktuellem Ubuntu vorinstalliert).

---

## Woher kommt der Node-Client?

Der Agent ist Teil dieses Repositories im Ordner `node-agent/`. Es gibt kein
separates Download-Paket — der Schnellstart oben klont einfach das Repo. Wer den
Ordner lieber ohne Git überträgt:

```bash
# vom Server/Arbeitsrechner aus auf den neuen Node kopieren:
rsync -a node-agent/ root@<node-host>:/opt/hydrahive-node-agent/
# dann auf dem Node:  cd /opt/hydrahive-node-agent && sudo sh scripts/setup.sh
```

---

## Was macht das Setup-Skript technisch?

`scripts/setup.sh` ruft intern `scripts/install.sh` auf. Das:
- legt den gesperrten System-Benutzer `hydrahive-node` an und hängt ihn in die
  Gruppe `incus-admin`,
- erstellt `/var/lib/hydrahive-node/` (`0700`) für Identität und Zustand,
- installiert das Paket (CLI `hydrahive-node`),
- installiert die gehärtete systemd-Unit und aktiviert sie.

Die Kopplung selbst läuft über `hydrahive-node enroll`. Der Agent erzeugt lokal
ein Schlüsselpaar, sendet einen Zertifikatsantrag (CSR) und zeigt einen
Fingerprint, den du im Cockpit bestätigst. Erst nach der Freigabe nimmt der Node
Arbeit an.

---

## Einmalige Server-Einrichtung (nur Server-Admin)

> Das macht **einmal** die Person, die den HydraHive-Server betreibt. Danach
> können beliebig viele Nodes über den Schnellstart oben dazukommen, ohne dass
> hier nochmal etwas angefasst werden muss.

Der Agentkanal ist mit gegenseitigem TLS (mTLS) abgesichert: Der Node meldet sich
mit einem Client-Zertifikat, das die HydraHive-**Compute-CA** ausgestellt hat. Ein
Reverse-Proxy vor dem Server prüft dieses Zertifikat und reicht die Identität plus
ein gemeinsames Geheimnis ans Backend weiter.

**1. Proxy-Secret setzen** (in der Server-Umgebung, z. B. `/etc/hydrahive2/env`):
```
HH_COMPUTE_PROXY_SECRET=<langes-zufälliges-secret>
```
Danach den HydraHive-Dienst neu starten. Die Compute-CA wird automatisch beim
ersten Enrollment erzeugt (`<config>/compute-pki/ca-cert.pem`).

**2. Reverse-Proxy** (Beispiel nginx) für den WSS-Endpunkt:
```nginx
location /api/compute/agent/connect {
    ssl_verify_client       on;
    ssl_client_certificate  /etc/hydrahive2/compute-pki/ca-cert.pem;

    proxy_set_header X-HydraHive-Client-Cert   $ssl_client_escaped_cert;
    proxy_set_header X-HydraHive-Proxy-Secret  "<dasselbe-secret-wie-oben>";
    proxy_set_header X-HydraHive-Node-ID       $http_x_hydrahive_node_id;

    proxy_http_version 1.1;
    proxy_set_header Upgrade    $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_pass http://127.0.0.1:8001;
}
```

Das Backend prüft fail-closed: ohne gültiges, von der Compute-CA signiertes
Client-Zertifikat **und** korrektes Proxy-Secret wird die Verbindung mit
`4403 agent_identity_invalid` abgewiesen. Ein im Cockpit widerrufener Node kann
sich nicht mehr verbinden.

Ausführliches Betriebs-Runbook (Recovery, Widerruf, Sicherheitsgrenzen):
[`../docs/compute-node-runbook.md`](../docs/compute-node-runbook.md).

---

## Manuelle Kopplung (ohne Setup-Skript)

Falls du die Schritte einzeln steuern willst:
```bash
sudo ./scripts/install.sh
umask 077; printf '%s' '<TOKEN>' > /run/hh-node-token
sudo -u hydrahive-node hydrahive-node enroll \
    --server https://<server> --name <node-name> \
    --token-file /run/hh-node-token \
    --ca-file /etc/hydrahive2/compute-pki/ca-cert.pem
rm -f /run/hh-node-token
# Fingerprint im Cockpit freigeben, dann:
sudo systemctl enable --now hydrahive-node
```
Token-Alternativen: `--token-stdin` oder ganz ohne Flag (interaktive Abfrage).

---

## Troubleshooting

| Symptom | Ursache / Lösung |
|---|---|
| `incus admin init` verlangt | Incus zuerst einrichten, Bridge `br0` erstellen lassen. |
| Kopplung „fehlgeschlagen" | Server-Adresse falsch/nicht erreichbar, oder Token abgelaufen/verbraucht → im Cockpit neuen Token erzeugen. |
| Node bleibt **„Wartet"** | Im Cockpit noch nicht **„Freigeben"** geklickt (Fingerprint bestätigen). |
| Verbindung bricht mit `4403` ab | Server-Einrichtung unvollständig: Proxy-Secret oder Reverse-Proxy fehlt/falsch, oder Node wurde widerrufen. |
| Node **„degraded"** | Health-Warnung (z. B. Incus-Socket nicht erreichbar). `journalctl -u hydrahive-node`. |
| VMs nicht auswählbar | `/dev/kvm` fehlt → Node kann nur Container. |

---

## Entwicklung / Tests

```bash
cd node-agent
python3 -m venv .venv && . .venv/bin/activate
pip install -e . pytest
PYTHONPATH="$PWD/src" pytest -q
```
