# HydraHive-Server: Ubuntu 24.04 auf 26.04 aktualisieren

**Freigabestand:** 2026-08-19

**Getesteter Pfad:** Ubuntu 24.04.4 LTS → Ubuntu 26.04 LTS

**Gilt für:** bestehende HydraHive-2.0-Server auf Ubuntu 24.04
**Wartungsfenster:** mindestens 2 Stunden einplanen

> Das Ubuntu-Upgrade und das HydraHive-Update sind zwei getrennte Vorgänge.
> `installer/update.sh` startet kein Betriebssystem-Upgrade. Es repariert
> HydraHive nach dem Ubuntu-Upgrade selbstständig.

## Kurzfassung

```bash
# 1. Auf Ubuntu 24.04 zuerst HydraHive auf den freigegebenen Stand bringen
sudo /opt/hydrahive2/installer/update.sh

# 2. Externen VM-/Container-Snapshot oder vollständiges Host-Backup erstellen
#    (außerhalb von HydraHive)

# 3. Ubuntu 24.04 vollständig aktualisieren
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y update-manager-core

# 4. Ubuntu-Release-Upgrade starten (siehe wichtigen Hinweis zu -d unten)
sudo do-release-upgrade
# Falls 26.04 am 2026-08-19 noch nicht regulär angeboten wird:
sudo do-release-upgrade -d

# 5. Nach dem Reboot HydraHive reparieren/aktualisieren
sudo /opt/hydrahive2/installer/update.sh

# 6. PostgreSQL-Daten kontrolliert von 16 auf 18 migrieren
sudo /opt/hydrahive2/installer/migrate-postgresql-cluster.sh --yes

# 7. Abschließend neu starten
sudo reboot
```

Die Kurzfassung ersetzt **nicht** die Backup- und Prüfhinweise unten.

---

## Wichtiger Hinweis zum heutigen `-d`-Kanal

Am 2026-08-19 meldet der normale LTS-Kanal auf dem Testsystem noch kein Upgrade,
der Frühupgrade-Kanal dagegen ausdrücklich:

```text
New release '26.04 LTS' available.
```

Der produktiv bevorzugte Befehl bleibt:

```bash
sudo do-release-upgrade -c
sudo do-release-upgrade
```

Nur wenn `-c` noch kein 26.04 anbietet und das Upgrade **heute ausdrücklich**
erfolgen soll, wurde folgender Pfad real getestet:

```bash
sudo do-release-upgrade -d
```

`-d` umgeht die übliche Wartefrist bis zur regulären LTS-Freigabe. Deshalb ist
ein externer Snapshot bzw. ein vollständiges Host-Backup zwingend. Sobald der
normale Kanal 26.04 anbietet, `-d` nicht mehr verwenden.

---

## 1. Voraussetzungen und Preflight

### Unterstützte Ausgangslage

```bash
. /etc/os-release
echo "$PRETTY_NAME"
python3 --version
pg_lsclusters
```

Erwartet vor dem Upgrade:

- Ubuntu 24.04.x LTS
- Python 3.12.x
- PostgreSQL `16 main` online auf Port 5432
- HydraHive und AgentLink aktiv

```bash
systemctl is-active hydrahive2 agentlink nginx postgresql redis-server
```

Alle Ausgaben müssen `active` sein.

### Freier Speicher

```bash
df -h /
sudo du -sh /var/lib/postgresql /var/lib/hydrahive2 /opt/hydrahive2
```

Für Betriebssystem, parallelen PostgreSQL-18-Cluster und Backups ausreichend
freien Speicher bereitstellen. Das PostgreSQL-Migrationsskript prüft später
zusätzlich konservativ auf mindestens dreimal die Größe des alten Clusters plus
1 GiB Reserve.

### Locale vor dem Release-Upgrade reparieren

Inkonsistente Locale-Variablen erzeugen beim Ubuntu-Upgrader Warnungen. Vorher:

```bash
sudo locale-gen en_US.UTF-8 de_DE.UTF-8
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
locale
```

### HydraHive noch auf 24.04 aktualisieren

```bash
sudo /opt/hydrahive2/installer/update.sh
```

Das ist wichtig: Dadurch liegt der Self-Heal-Code bereits lokal vor, selbst wenn
HydraHive nach dem OS-Reboot vorübergehend nicht startet.

---

## 2. Backup und Rückfallpunkt

### Bevorzugt: Snapshot außerhalb von HydraHive

- VM: Hypervisor-Snapshot
- Incus/LXC: Snapshot auf dem äußeren Incus-Host
- Bare Metal: vollständiges Image-/Dateisystem-Backup

Beispiel auf einem Incus-Host:

```bash
incus snapshot create <container-name> before-ubuntu-2604
incus snapshot list <container-name>
```

Auf `dir`-Storage wird der Snapshot per rsync kopiert und kann mehrere Minuten
dauern. Erst fortfahren, wenn `incus operation list` keinen laufenden
Snapshot-Vorgang mehr zeigt.

HydraHive besitzt aktuell noch keine Container-Snapshot-Funktion im Cockpit.
Das ist separat als Feature geplant; der Snapshot muss heute auf dem äußeren
Host angelegt werden.

### Zusätzlich: logisches Datenbank- und Hydra-Datenbackup

```bash
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
sudo install -d -m 700 /var/backups/hydrahive2
sudo bash -o pipefail -c \
  "runuser -u postgres -- pg_dumpall | gzip -9 > '/var/backups/hydrahive2/postgresql-before-os-upgrade-$STAMP.sql.gz'"
sudo gzip -t "/var/backups/hydrahive2/postgresql-before-os-upgrade-$STAMP.sql.gz"
sudo sha256sum "/var/backups/hydrahive2/postgresql-before-os-upgrade-$STAMP.sql.gz" \
  | sudo tee "/var/backups/hydrahive2/postgresql-before-os-upgrade-$STAMP.sql.gz.sha256"

sudo tar -C / --xattrs --acls -czf \
  "/var/backups/hydrahive2/hydrahive-data-before-os-upgrade-$STAMP.tar.gz" \
  etc/hydrahive2 var/lib/hydrahive2
sudo chmod 600 /var/backups/hydrahive2/*
```

Das Backup enthält Datenbankrollen und Kennworthashes. Es muss mit Modus 0600
und außerhalb öffentlich erreichbarer Verzeichnisse bleiben.

---

## 3. Ubuntu aktualisieren

Für Remote-Systeme den Vorgang in einer Hypervisor-Konsole oder in `tmux`
ausführen. Während des Paketwechsels kann SSH vorübergehend neu gestartet
werden.

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y update-manager-core
sudo do-release-upgrade -c
```

Wenn der normale Kanal 26.04 anbietet:

```bash
sudo do-release-upgrade
```

Nur für den am 2026-08-19 getesteten Frühupgrade-Pfad:

```bash
sudo do-release-upgrade -d
```

Bei Rückfragen zu lokal geänderten HydraHive-/nginx-/PostgreSQL-Konfigurationen
die vorhandene lokale Konfiguration behalten. Den Ubuntu-Upgrader vollständig
beenden lassen und den verlangten Neustart durchführen.

### Erwartetes Verhalten nach dem ersten Reboot

Ubuntu 26.04 entfernt Python 3.12. Alte Installationen hatten:

```text
/opt/hydrahive2/.venv/bin/python -> python3.12
/opt/hydralink/.venv/bin/python  -> python3.12
```

HydraHive und AgentLink können daher zunächst mit `status=203/EXEC` ausfallen.
Das ist im getesteten Ablauf erwartet und wird im nächsten Schritt repariert.
nginx, SSH, Redis und der alte PostgreSQL-16-Cluster bleiben erreichbar.

Zwei weitere Änderungen nimmt Ubuntu 26.04 am Host vor. Beide werden von
`update.sh` automatisch behoben (Schritt 4); dieser Abschnitt beschreibt sie,
damit die Symptome zuzuordnen sind.

#### `/tmp` liegt danach im RAM

Ubuntu 26.04 aktiviert die Vendor-Unit `tmp.mount`. `/tmp` wird dadurch ein
`tmpfs` und liegt im Arbeitsspeicher statt auf der Platte:

```bash
findmnt -no FSTYPE,SIZE /tmp
```

Zeigt das `tmpfs`, ist der Zustand vorhanden. Läuft `/tmp` voll — etwa beim
Kopieren großer Mediendateien — geraten RAM und Swap unter Druck,
SQLite-Commits blockieren und das Backend meldet `database is locked`, im
Streaming-Bereich als „Internal Error“. `update.sh` maskiert `tmp.mount`; wirksam
wird das beim nächsten Reboot (Schritt 6).

#### Der DNS-Stub verdrängt einen lokalen DNS-Server

Das Upgrade setzt `/etc/systemd/resolved.conf` auf den Werkszustand zurück. Wer
auf demselben Host Pi-hole, dnsmasq, bind9 oder unbound betreibt, verliert
dadurch die Namensauflösung — der Stub-Listener belegt Port 53 zuerst.

Verschärfend kommt hinzu: Incus startet je verwalteter Bridge einen eigenen
`dnsmasq`, der TCP auf der Bridge-IP `:53` hält und den Wildcard-Bind ebenfalls
blockiert.

Typische Meldung im Journal des DNS-Servers:

```text
dnsmasq: failed to create listening socket for port 53: Address in use
```

> **Achtung:** `systemctl is-active pihole-FTL` meldet in diesem Fall trotzdem
> `active`. Der Ausfall entgeht jedem Healthcheck, der nur den Unit-Status
> prüft. Verlässlich ist allein eine echte Abfrage:
>
> ```bash
> dig +short github.com @127.0.0.1
> ```

`update.sh` schaltet den Stub-Listener per Drop-in ab, hängt `/etc/resolv.conf`
auf den echten Resolver um und deaktiviert den DNS-Teil der Incus-Bridges
(`raw.dnsmasq port=0`) — DHCP der Container bleibt dabei erhalten.

---

## 4. HydraHive und AgentLink selbstheilend reparieren

```bash
sudo /opt/hydrahive2/installer/update.sh
```

Der neue Updatepfad:

1. erkennt einen fehlenden oder falschen Venv-Interpreter;
2. stoppt den betroffenen Dienst vor dem Rebuild;
3. installiert nötigenfalls `python3-venv`;
4. baut das Venv kontrolliert mit `--clear` auf Python 3.14 neu;
5. installiert Core und Abhängigkeiten über `python -m pip`;
6. repariert fehlendes npm reproduzierbar auf npm 11.6.2;
7. baut das Frontend;
8. aktualisiert AgentLink und repariert dessen Venv ebenfalls;
9. startet vorhandene Voice-Container und setzt `boot.autostart=true`;
10. maskiert `tmp.mount`, wenn `/tmp` als `tmpfs` im RAM liegt;
11. stellt `DNSStubListener=no` wieder her, sofern ein lokaler DNS-Server läuft;
12. schaltet den DNS-Teil verwalteter Incus-Bridges ab (DHCP bleibt aktiv);
13. prüft die Namensauflösung real und startet den DNS-Server notfalls neu.

Die Schritte 10 bis 13 laufen nur an, wenn der jeweilige Fehlerzustand
tatsächlich vorliegt. Auf einem Server ohne eigenen DNS-Dienst bleibt der
`systemd-resolved`-Stub unangetastet.

Erwartete Logzeilen beim ersten Lauf:

```text
Python-venv: Zielinterpreter /usr/bin/python3 (Python 3.14.x)
Python-venv fehlt oder ist inkompatibel — baue mit --clear neu
AgentLink-venv: bin/python fehlt ... — baue venv neu (--clear)
Update erfolgreich, Service läuft.
```

Falls npm beim OS-Upgrade entfernt wurde:

```text
npm fehlt — repariere Node-Toolchain
Preparing npm@11.6.2 for immediate activation...
```

Prüfen:

```bash
/opt/hydrahive2/.venv/bin/python --version
/opt/hydralink/.venv/bin/python --version
npm --version
systemctl is-active hydrahive2 agentlink agentlink-frontend nginx redis-server
```

Erwartet: beide Venvs Python 3.14.x, npm 11.6.2 und alle Dienste `active`.

Zusätzlich auf Hosts mit eigenem DNS-Server:

```bash
dig +short github.com @127.0.0.1        # muss eine IP liefern
systemctl is-enabled tmp.mount           # erwartet: masked
```

---

## 5. PostgreSQL 16 kontrolliert auf 18 migrieren

Nach dem Ubuntu-Upgrade läuft zunächst weiterhin `16 main` auf Port 5432. Das
ist absichtlich sicherer als eine unbemerkte automatische Datenmigration.

Status prüfen:

```bash
pg_lsclusters
```

Dann:

```bash
sudo /opt/hydrahive2/installer/migrate-postgresql-cluster.sh --yes
```

Das Skript:

- verlangt explizit `--yes` und root;
- verhindert parallele Läufe per `flock`;
- prüft freien Speicher;
- installiert PostgreSQL 18 und `postgresql-18-pgvector`;
- führt `pg_upgradecluster --check` aus;
- erstellt ein vollständiges `pg_dumpall`-Backup unter
  `/var/backups/hydrahive2/`;
- prüft gzip und erzeugt eine SHA-256-Datei;
- stoppt HydraHive und AgentLink während der Migration;
- migriert sicher per dump/restore;
- baut Indizes für die neue libc-Collation neu;
- prüft Datenbanken und Vector-Erweiterung;
- startet die Dienste wieder;
- **löscht den alten PostgreSQL-16-Cluster nicht**.

Erwartet danach:

```text
16  main  5433  down
18  main  5432  online
```

Prüfen:

```bash
pg_lsclusters
sudo -u postgres psql -d hydrahive_mirror -Atc \
  "SELECT extversion FROM pg_extension WHERE extname='vector'"
sudo sha256sum -c /var/backups/hydrahive2/*.sha256
```

Der alte Cluster bleibt mindestens bis nach der vollständigen Kundenabnahme als
Rollback-Punkt erhalten. Nicht am selben Abend löschen.

---

## 6. Abschließender Reboot und Abnahme

```bash
sudo reboot
```

Danach:

```bash
systemctl is-active hydrahive2 agentlink agentlink-frontend nginx postgresql redis-server
pg_lsclusters
/opt/hydrahive2/.venv/bin/python --version
/opt/hydralink/.venv/bin/python --version
npm --version
```

`/tmp` muss jetzt wieder auf der Platte liegen — erst der Reboot macht die
Maskierung von `tmp.mount` wirksam:

```bash
findmnt -no FSTYPE,SIZE /tmp
```

Erwartet: das Dateisystem der Root-Platte (z. B. `ext4`), **nicht** `tmpfs`.

Auf Hosts mit eigenem DNS-Server (Pi-hole, dnsmasq, bind9, unbound) zusätzlich:

```bash
dig +short github.com @127.0.0.1
ss -lunp 'sport = :53'
```

Erwartet: eine IP-Adresse, und der eigene DNS-Server auf `0.0.0.0:53`. Taucht
dort stattdessen `systemd-resolve` auf `127.0.0.53` oder ein `dnsmasq` auf einer
Incus-Bridge-IP auf, greift der Self-Heal nicht — dann Abschnitt 3 erneut lesen.

Wenn Voice installiert ist:

```bash
incus list -c ns --format csv
incus config get hydrahive2-stt boot.autostart
incus config get hydrahive2-tts boot.autostart
ss -ltn | grep -E '127.0.0.1:(10200|10300)'
```

Erwartet:

- STT und TTS `RUNNING`
- beide Autostart-Werte `true`
- Ports 10200 und 10300 erreichbar

API-Abnahme:

```bash
curl -k https://127.0.0.1/api/health
```

Zusätzlich im Cockpit prüfen:

- Login funktioniert
- Projekte und Agenten vorhanden
- bestehende Sessions vorhanden
- Buddy antwortet
- AgentLink-Status grün
- Voice-Status grün, falls installiert

### LXC-Hinweis: netplan-configure

In einem verschachtelten Ubuntu-26.04-LXC kann diese Unit fehlschlagen:

```text
netplan-configure.service: udevadm: No such file or directory
```

Wenn der Container seine korrekte IP hat, SSH funktioniert und die oben
genannten Ports erreichbar sind, ist das eine LXC-/udev-Eigenheit und kein
HydraHive-Ausfall. Auf Bare Metal oder einer echten VM trat dieser Gast-spezifische
Befund nicht auf.

---

## 7. Rollback

### Vollständiges OS-Rollback

Ein Ubuntu-Release-Upgrade lässt sich nicht zuverlässig per apt zurückrollen.
Bei grundlegendem Fehler den externen VM-/Container-Snapshot bzw. das
vollständige Host-Backup wiederherstellen.

### Nur PostgreSQL zurück auf 16

Das Migrationsskript gibt am Ende die konkreten Ports aus. Typischer Zustand:
PG18 auf 5432, alter PG16 auf 5433.

```bash
sudo systemctl stop hydrahive2 agentlink
sudo pg_ctlcluster 18 main stop
sudo pg_conftool 18 main set port 5433
sudo pg_conftool 16 main set port 5432
sudo pg_ctlcluster 16 main start
sudo systemctl start hydrahive2 agentlink
```

Danach sofort `pg_lsclusters` und die APIs prüfen. Nicht gleichzeitig beide
Cluster auf demselben Port starten.

---

## Real verifizierter Testlauf

Ausgang:

- Ubuntu 24.04.4
- Python 3.12.3
- PostgreSQL 16.14
- Node 20.20.2
- ffmpeg 6.1.1
- zwei Voice-Incus-Container

Ziel nach echtem Release-Upgrade, Reparatur, PG-Migration und finalem Reboot:

- Ubuntu 26.04 LTS
- Python 3.14.4 in beiden Venvs
- PostgreSQL 18.4 auf Port 5432
- PostgreSQL 16 gestoppt auf Port 5433 als Rollback
- Vector 0.8.1
- Node 22.22.1 und npm 11.6.2
- HydraHive, AgentLink, nginx, PostgreSQL und Redis aktiv
- Voice-STT/TTS `RUNNING`, beide mit Autostart
- `/api/health`, Projekte, Sessions, Agenten, AgentLink und Buddy: HTTP 200
- Sentinel-Projekt, Sentinel-Datei und Testsession unverändert vorhanden
- Datenbanktabellen vor/nach Migration identisch
- Backup-Prüfsumme erfolgreich
- 2061 Core-Tests bestanden
