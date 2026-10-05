# Container auf VPS: NAT-Netz und Portfreigaben

**Stand:** 05.10.2026 · **Status:** freigegeben von Till · **Task:** fa358d87
**Verwandt:** `containers/`, `installer/modules/70-containers.sh`, `server-peering.md`

## Problem

Container kennen heute zwei Netzmodi (`containers/models.py`):

- **bridged:** eigene NIC an `br0`, IP per DHCP vom Heimrouter.
- **isolated:** kein Netz.

Auf einem VPS gibt es weder `br0` noch einen DHCP-Server, der weitere öffentliche
IPs vergibt. Container lassen sich dort also nicht sinnvoll betreiben.
Ziel: Container auf dem VPS anlegen und ihre Dienste **gezielt** erreichbar
machen – öffentlich (z. B. Gameserver), nur fürs Tailnet (Admin-Oberflächen)
oder gar nicht.

## Entscheidungen

1. Neuer Netzmodus **`nat`**: eigenes incus-Netz mit NAT nach außen.
2. **Portfreigaben pro Container**, nicht ein Schalter pro Container.
3. **Reichweite pro Freigabe**: `public` | `tailnet` | `off` (Till, 05.10.2026).
4. Portbereiche und UDP sind Pflicht (Gameserver).

## Netz

- incus-Netz **`hhnat0`**, IPv4 `10.10.0.1/24`, NAT an, IPv6 aus.
- Jeder NAT-Container bekommt eine **feste** IP aus `10.10.0.10–10.10.0.250`
  (`ipv4.address` am NIC-Device), damit Freigaben nach einem Neustart weiter stimmen.
- Container erreichen das Internet (Updates, Downloads) über NAT.
- **Installer:** Gibt es kein `br0`, legt `70-containers.sh` `hhnat0` an.
  Gibt es `br0`, bleibt alles wie bisher. `hhnat0` kann zusätzlich angelegt werden.
- **Standardmodus beim Anlegen:** `bridged`, wenn `br0` existiert, sonst `nat`.
  Die Oberfläche fragt `GET /api/containers/network-modes` und graut fehlende
  Modi aus.

## Portfreigaben

Eine Freigabe hat:

| Feld | Werte |
|---|---|
| `protocol` | `tcp` · `udp` |
| `host_port_start` / `host_port_end` | 1024–65535, Ende ≥ Start, max. 100 Ports pro Freigabe |
| `container_port_start` | Bereich wird 1:1 abgebildet |
| `scope` | `public` · `tailnet` · `off` |
| `label` | Freitext, max. 64 Zeichen |

„TCP + UDP“ legt die Oberfläche als zwei Freigaben an.

### Umsetzung

- incus **proxy device** pro Freigabe:
  `listen=<proto>:<adresse>:<start>-<ende>`,
  `connect=<proto>:<container-ip>:<start>-<ende>`, `nat=true`.
  - `nat=true` leitet per Kernel weiter (kein Userspace-Proxy), die Client-IP
    bleibt sichtbar. **Bei der Umsetzung auf dem VPS live verifizieren.**
- **Adresse** je Reichweite:
  - `public` → öffentliche IPv4 des Servers (aus `ip route get 1.1.1.1`)
  - `tailnet` → Tailscale-IPv4 des Servers
  - `off` → kein Device, Regel bleibt nur in der DB
- **ufw** (falls aktiv), Kommentar `hh-port:<freigabe-id>`. Weil `nat=true`
  per DNAT weiterleitet, laufen die Pakete durch die **FORWARD**-Kette, also
  `ufw route` (nicht `ufw allow`), Ziel ist die Container-IP und der Container-Port:
  - `public` → `ufw route allow in on <wan-if> out on hhnat0 to <ip> port <cports> proto <proto>`
  - `tailnet` → dasselbe mit `in on tailscale0`
  - `off` → Regeln mit dem Kommentar entfernen

### Live-Befund VPS (05.10.2026)

Mit Testcontainer `debian/12` an `hhnat0`, feste IP `10.10.0.10`, getestet von .2:

| Test | Ergebnis |
|---|---|
| Container → Internet (`apt-get install`) | ✅ |
| TCP 25565 öffentlich, nur Proxy-Device ohne ufw-Route-Regel | ❌ Timeout (ufw FORWARD DROP) |
| TCP 25565 öffentlich mit `ufw route allow` | ✅, Container sieht **echte Client-IP** 37.24.27.133 |
| TCP über Tailnet (28443 → 25565) | ✅, Container sieht 10.10.0.1 (Tailscale maskiert, Client-IP geht verloren) |
| UDP über Tailnet (27016 → 27015) | ✅ |
| UDP 27015 öffentlich | ❌ kommt am VPS gar nicht an (tcpdump 0 Pakete): Anbieter-Firewall lässt nur TCP + ICMP durch |

Folgen:
- Hinweis in der Oberfläche bei `public` + UDP: Anbieter-Firewall muss UDP erlauben.
- Bei `tailnet` sieht der Dienst nicht die echte Absender-IP (Tailscale-Masquerade). Für Admin-Zugänge unkritisch.
- Ausführung als root über einen schmalen Helfer
  (`/usr/local/sbin/hh-portforward`, sudoers nur für diesen Befehl) mit eigener
  Eingabeprüfung. Das Backend ruft nie direkt `ufw` auf.

### Schutz

- **Gesperrte Host-Ports:** 22, 53, 80, 443, 5432, 6379, 8001, 8888, 9000, 9001,
  10000, 41641, 3000, 3001 und alles unter 1024.
- **Keine Doppelbelegung:** gleiches Protokoll + überlappender Bereich auf
  demselben Server wird abgewiesen (`container_port_conflict`).
- Freigaben nur für Container im Modus `nat`.
- Anlegen/Ändern von `public`: nur Admin oder Capability `containers.public_ports`.
- Container löschen → alle Freigaben samt ufw-Regeln weg.
- **Anbieter-Firewall** (z. B. Hostinger) kann HydraHive nicht steuern. Die
  Oberfläche zeigt bei `public` einen Hinweis mit den zu öffnenden Ports.

## Datenmodell (Migration 054)

`containers.ipv4` TEXT NULL (feste IP bei `nat`)

`container_ports`
- `id`, `container_id` → containers (CASCADE)
- `protocol`, `host_port_start`, `host_port_end`, `container_port_start`
- `scope`, `label`, `created_at`, `applied_at`, `last_error`

`network_mode` erlaubt zusätzlich `nat`.

## API

- `GET /api/containers/network-modes` → `{bridged: bool, nat: bool, isolated: true, default}`
- `GET /api/containers/{id}/ports`
- `POST /api/containers/{id}/ports`
- `PATCH /api/containers/{id}/ports/{port_id}` (v. a. `scope`)
- `DELETE /api/containers/{id}/ports/{port_id}`

Fehlercodes: `container_port_reserved`, `container_port_conflict`,
`container_port_range_invalid`, `container_port_not_nat`,
`container_port_public_forbidden`, `container_port_apply_failed`.

## Oberfläche

- **Container anlegen:** Netzmodus mit Erklärung, nicht verfügbare Modi ausgegraut.
- **Container-Detail → „Ports“:** Tabelle wie im Beispiel unten, Reichweite als
  Dreifach-Schalter 🌍 / 🔒 / ⛔, Hinweis zur Anbieter-Firewall.

| Freigabe | Protokoll | außen → innen | Reichweite |
|---|---|---|---|
| Minecraft | TCP | 25565 → 25565 | 🌍 öffentlich |
| Spiel | UDP | 27000–27015 → 27000–27015 | 🌍 öffentlich |
| Admin | TCP | 8443 → 443 | 🔒 Tailnet |

## Nicht-Ziele (vorerst)

- Webdienste per Subdomain + Let's Encrypt (eigene Spec)
- IPv6-Freigaben
- Container auf Remote-Nodes (`node_id != local`) – Freigaben nur lokal

## Akzeptanzkriterien

1. VPS: Container im Modus `nat` anlegen → hat feste `10.10.0.x`, kommt ins Internet.
2. Freigabe TCP 25565 `public` → von außen erreichbar (nach Öffnen der Anbieter-Firewall).
3. Gleiche Freigabe auf `tailnet` → nur noch über Tailscale-IP erreichbar, von außen nicht.
4. `off` → nirgends erreichbar, Regel bleibt sichtbar.
5. UDP-Bereich 27000–27015 funktioniert.
6. Gesperrter Port (z. B. 22) und Überlappung → abgewiesen.
7. Container löschen → Proxy-Devices und ufw-Regeln weg.
8. .2: bestehende bridged Container unverändert.

## Etappen

1. Installer: incus auf VPS, `hhnat0`, Fix für fehlende ReadWritePaths-Ordner
2. Netzmodus `nat` + feste IP (Backend + Anlegen-Dialog)
3. Portfreigaben: DB, API, Root-Helfer, ufw
4. Oberfläche „Ports“
5. Live-Abnahme auf dem VPS
