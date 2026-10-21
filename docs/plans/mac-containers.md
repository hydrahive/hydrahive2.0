# Plan: Container auf dem Mac (Colima + Incus)

Status: **FREIGEGEBEN** (Till 21.10.2026: bauen; Container als Option, Standard aus; Portfreigaben Weg **A**). Task f4a303a9, Etappe 2 (Etappe 1 = AgentLink, `mac-agentlink.md`).

Ziel (Till, 21.10.2026): Container auf dem Mac **wie unter Linux**, von Agenten verwaltbar. Randbedingung: **Der
Linux-Installer darf nicht kaputtgehen.**

## 1. Machbarkeit – auf dem Intel-Test-Mac .186 ausprobiert (21.10.2026)

Alles in einem Wegwerf-Ordner (`~/.hh-probe`), danach restlos entfernt. HydraHive selbst blieb unberührt.

| Prüfung | Ergebnis |
|---|---|
| Colima 0.10.3 + Lima 2.2.1 + Incus-Client 7.0.2 als **fertige Dateien von GitHub** (Prüfsummen ok), **ohne Homebrew** | ✅ |
| `colima start --runtime incus --vm-type vz` (Apple Virtualization) | ✅ Linux-VM mit Incus 7.1 (zfs), Start in ~2 min, Neustart der VM ~50 s |
| Der **unveränderte Kern-Code** gegen dieses Incus (`incus_client.is_available/list_running_names/info/list_images`, Zusatz-Modul-Prüfung) | ✅ alles ok, 1.883 Images |
| `incus_client.launch(network_mode="nat", ipv4=…)` + `add_proxy_device` + stop/start/restart/delete | ✅ (mit `hhnat0` in der VM) |
| Container hat Internet (DNS, apt) – Netz `incusbr0` und `hhnat0` | ✅ (Debian; Alpine bekam per Hand-Test keine Adresse – Testfehler meinerseits, Kern setzt die IP fest) |
| Container vom Mac aus erreichbar | ✅ über Route 192.168.100.0/24 → VM; Proxy-Port über VM-IP 200 |
| Colima als **LaunchDaemon** (`colima start --foreground`, `UserName`) | ✅ |
| **Neustart des Macs ohne Anmeldung** (`0 users`) | ✅ VM + Container laufen wieder, AgentLink ebenfalls |
| Speicher | VM 2 GB → ~1,2 GB auf der Mac-Seite; Platte ~4 GB nach einem Container |

**Wie Agenten Container verwalten (heute, Linux):** Es gibt **kein** eigenes Container-Werkzeug für Agenten
(Spec `agent-infrastructure-tools.md` ist ein Entwurf). Agenten nutzen `shell_exec` mit `incus …`; der
Harakiri-Schutz kennt `incus exec` schon (`tools/_container_exec.py`). Auf dem Mac geht genau das, sobald `incus`
im PATH des Dienstes liegt und auf die Colima-VM zeigt – im Test lief `incus` ohne jede Einstellung
(Remote steht in `~/Library/Application Support/incus/config.yml`).

**Warum Colima + Incus und nicht Docker:** Unser Kern spricht Incus über die Kommandozeile `incus`
(`containers/incus_client.py`). Colima bringt ein echtes Incus mit und richtet den `incus`-Befehl am Mac so ein,
dass er die VM anspricht. Damit läuft **derselbe Code** wie unter Linux – Container-Seite, Reconciler, Agenten.

**Warum Downloads statt Homebrew:** Homebrew hat für Intel-Macs keine fertigen Pakete von `lima`, `colima`
und `incus` mehr (nur `arm64_*`) – wie bei Redis würde alles aus dem Quellcode gebaut. Die Projekte veröffentlichen
fertige Mac-Dateien mit Prüfsummen für **beide** Architekturen. Auf Apple Silicon ginge Homebrew, aber ein Weg
für beide ist einfacher zu pflegen und zu testen.

## 2. Was auf dem Mac anders ist als unter Linux

| Linux | Mac | Folge |
|---|---|---|
| Incus direkt auf dem Host | Incus in einer Linux-VM (Colima) | eigener LaunchDaemon `io.hydrahive.colima` |
| Netzwerkbrücke `br0` → Container im Heimnetz | gibt es nicht | Modus **bridged entfällt**; Standard **nat** (`hhnat0`, 10.10.0.0/24 wie VPS) |
| `nat.py` prüft `/sys/class/net/hhnat0` | `/sys` gibt es nicht → heute „nur isolated“ | Prüfung über `incus network show` statt `/sys` (nur auf dem Mac) |
| Portfreigabe: proxy device auf **WAN-IP des Hosts** + ufw-Regel per `sudo hh-portforward` | WAN-IP des Macs gibt es in der VM nicht, kein ufw, kein Root-Helfer | Freigabe „public“ = Port an der **VM-Adresse** + Weiterleitung Mac → VM (siehe §4) |
| Tailnet-Freigabe | Tailscale läuft auf dem Mac, nicht in der VM | wie „public“, nur an die Tailscale-IP gebunden |
| VMs (`65-vms.sh`, QEMU/libvirt) | – | **nicht** in diesem Plan (Incus-VMs laut Colima erst ab M3, verschachtelt) |

## 3. Bauteile

### Installer (nur Mac-Dateien – Linux-Installer bleibt unangetastet)
- **neu** `installer/modules-mac/70-containers.sh`:
  - lädt Colima, Lima, Incus-Client in fester Version nach `/usr/local/lib/hydrahive2/containers/<version>/`
    (passend zur Architektur `arm64`/`x86_64`), **prüft SHA-256** gegen fest im Skript hinterlegte Werte,
    verlinkt nach `/usr/local/lib/hydrahive2/containers/bin` (Ordner gehört dem Dienstnutzer)
  - startet einmal `colima start hydrahive --runtime incus --vm-type vz --cpu N --memory M --disk D`
    (Werte aus `HH_CONTAINERS_CPU/MEMORY/DISK`, Standard 2 / 4 GB / 60 GB, gedeckelt auf Hälfte RAM/Kerne)
  - legt `hhnat0` an (gleiche Werte wie `installer/lib/container-nat.sh`)
  - schreibt LaunchDaemon `io.hydrahive.colima` (`UserName=$HH_USER`, `colima start hydrahive --foreground`,
    `COLIMA_HOME` unter `/usr/local/var/hydrahive2/colima`)
  - trägt `HH_INSTALL_CONTAINERS=yes` in `install.conf` ein; der Backend-PATH bekommt den bin-Ordner
- `install-mac.sh`: Phase „Container“ **nur auf Wunsch** (`HH_INSTALL_CONTAINERS=yes` bzw. `--with=containers`),
  Standard **aus** – die VM kostet RAM, nicht jeder will das.
- `update-mac.sh`: wenn `HH_INSTALL_CONTAINERS=yes` → `70-containers.sh` erneut (neue Versionen, Daemon prüfen).
- Nachinstallieren aus dem Cockpit (Einstellungen → Zusatz-Module → Container): Mac-Gegenstück zu `addon-ctl.sh`
  (LaunchDaemon mit `WatchPaths` auf `.addon_request`, nur Modul `containers` erlaubt, gleiche Prüfungen).
- `50-launchd.sh`: PATH des Backends um den Container-bin-Ordner erweitern (nur wenn vorhanden).

### Kern (minimal, Linux-Verhalten unverändert)
- `containers/nat.py`: `bridge_available()`/`nat_available()` auf dem Mac nicht über `/sys`, sondern
  `incus network show hhnat0`; bridged dort immer `False`. Unter Linux **bleibt** die `/sys`-Prüfung.
- `containers/ports.py`: Portfreigabe auf dem Mac ohne `sudo hh-portforward`/ufw: proxy device lauscht auf der
  VM-Adresse, die Weiterleitung Mac → VM übernimmt ein kleiner Weiterleiter (siehe §4). Linux-Weg unverändert.
- `incus_client.host_is_lxc()` ruft `systemd-detect-virt` – auf dem Mac schon heute `False` (geprüft), bleibt.
- Auswahl des Weges über **eine** Stelle (`containers/_platform.py`: `is_mac()` = `sys.platform == "darwin"`),
  damit der Linux-Code nicht mit Mac-Abfragen durchsetzt wird.

### Doku
- `INSTALL-macOS(.de).md`: Abschnitt „Container (optional)“, Tabelle „Was auf dem Mac nicht geht“ anpassen.

## 4. Offene Entscheidung: Portfreigaben (Container von außen erreichbar)

Was ohne Zusatz schon geht: Container sind **vom Mac selbst** erreichbar (Route ins Container-Netz), Agenten können
sie anlegen, starten, darin Befehle ausführen. Für „Port 8080 des Containers im Heimnetz anbieten“ (Linux:
Reichweite public/tailnet) gibt es drei Wege:

- **A (gewählt, Till 21.10.):** kleiner Weiterleiter im Kern (asyncio, nur TCP), der je Freigabe auf `0.0.0.0:<port>` bzw. der
  Tailscale-IP des Macs lauscht und zur VM weiterreicht. Kein root nötig (Ports ≥ 1024 – die Linux-Regeln erlauben
  ohnehin nur 1024–65535). Nachteil: UDP nicht, Client-IP im Container ist die der VM.
- **B:** Colima mit `--network-address` (VM bekommt eine Adresse im Mac-Netz) + Lima-Port-Weiterleitung. Im Test
  leitete Lima die Ports in diesem Modus **nicht** weiter (Colima schaltet das für Incus bewusst ab).
- **C:** Portfreigaben auf dem Mac vorerst nicht anbieten (Oberfläche zeigt „auf dem Mac nicht verfügbar“).

## 5. Schutz für Linux („nicht killen“)

- Keine Änderung an `installer/install.sh`, `installer/update.sh`, `installer/modules/*`, `installer/lib/container-nat.sh`,
  `hh-portforward`.
- Kern-Änderungen nur hinter `is_mac()`; Linux-Pfade bekommen **Regressionstests**, die vorher und nachher grün sind
  (Netzmodi über `/sys`, ufw-Helfer-Aufruf bei Portfreigaben).
- Gegenprobe vor dem Merge: volle Suite + **echter Linux-Update-Lauf auf hydratest** (`update.sh`, Container-Seite,
  Container anlegen/löschen, Portfreigabe) – unverändertes Verhalten.

## 6. Reihenfolge (TDD, je Schritt rot → grün → Commit)

1. `_platform.is_mac()` + `nat.py` Mac-Zweig; Linux-Regressionstests für `/sys`-Weg.
2. `modules-mac/70-containers.sh` (Download + Prüfsumme + Arch, Colima-Start, `hhnat0`, LaunchDaemon) – Tests auf
   nachgebautem Mac (wie hydralink `tests/mac_fake.py`); falsche Prüfsumme → Abbruch ohne Installation.
3. `install-mac.sh`/`update-mac.sh`/`50-launchd.sh` (PATH) – optional, Standard aus.
4. Nachinstallieren aus dem Cockpit (Mac-Runner).
5. Portfreigaben nach Tills Entscheidung (§4).
6. Doku de/en.
7. Abnahme auf .186: Container-Seite zeigt Incus, Container anlegen (nat) per Oberfläche **und** per Agent
   (`shell_exec` mit `incus …` in einem echten Agenten-Lauf),
   Befehl im Container, stoppen/löschen, Neustart des Macs ohne Anmeldung → Container wieder da. Linux-Gegenprobe
   auf hydratest.

## 7. Akzeptanzkriterien

- [x] Mac mit Option „Container“: Container per API wie die Oberfläche (nat, 10.10.0.10) und per `shell_exec`-Werkzeug
  (`incus launch/exec/list/delete`) – live .186. Echter LLM-Agentenlauf nicht möglich: Codex-Token auf .186 widerrufen.
- [x] Nach Neustart des Macs ohne Anmeldung laufen VM und Container wieder; Portfreigabe nach ≤ 30 s wieder offen.
- [x] Ohne Option: nichts von Colima wird installiert (Standard aus; Test).
- [x] Downloads nur mit passender Prüfsumme (Test: falsche → Abbruch ohne Installation); Colima-Dienst unter dem Nutzer.
- [x] Linux: keine Änderung an Linux-Installer-Dateien (git diff leer); hydratest: update.sh ok, nat-Container +
  Portfreigabe über WAN-IP/ufw-Helfer + Löschen unverändert.

## 8. Nicht in diesem Plan

- Incus-VMs auf dem Mac (erst ab M3, eigener Schritt), QEMU/libvirt-VMs.
- SearXNG, Whisper, WhatsApp in Containern auf dem Mac (wäre der nächste Schritt, sobald Container laufen).
- Agent-Werkzeuge für Container (Spec `agent-infrastructure-tools.md`) – gilt für Linux und Mac gleich, eigener Task.

## Umsetzung (21.10.2026)

Befunde bei der echten Abnahme auf .186 (alle mit Test abgesichert):
1. `update-mac.sh` fand als root weder `npm` noch `node` („sudo: npm“ / „env: npm“) – **betraf jedes Mac-Update mit
   Frontend-Änderung**, auch auf main. Behoben (Homebrew-bin über vollen Pfad, `sudo -u … env PATH=…`).
2. Erster Colima-Start scheitert manchmal an `incus remote add … EOF` → einmal neu starten.
3. VM aus dem Installer lief neben dem Dienst → Neustart-Schleife „already running“ → VM an den Dienst übergeben;
   „gehört dem Dienst“ = `launchctl list` mit PID.
4. Backend-PATH ohne `/sbin` → `route`/`ipconfig` mit vollem Pfad.
5. Incus verbietet `0.0.0.0` mit `nat=true` → proxy device auf der VM-Adresse.
6. iMac mit WLAN + Kabel: „public“ lauscht jetzt auf allen Adressen des Macs.
