# Feature Map: VMs — QEMU/KVM Virtual Machines

> **Modul:** `core/src/hydrahive/vms/`  
> **Datenpfad:** `/var/lib/hydrahive2/vms/`  
> **Frontend:** `frontend/src/features/vms/`  
> **Was:** QEMU/KVM VM-Management. Lifecycle, Snapshots, VNC-Zugriff.  
> **Warum:** Agents können in isolierten VMs arbeiten. Auch für User: Desktop-VMs via Browser-VNC.

---

## Datenpfad-Struktur

```
/var/lib/hydrahive2/vms/
├── disks/          # VM-Disk-Images (.qcow2)
├── isos/           # ISO-Dateien für Installation
├── logs/           # VM-Logs
├── pids/           # PID-Dateien laufender VMs
└── vnc-tokens/     # VNC-Auth-Token (temporär)
```

---

## API-Endpoints

| Endpoint | Beschreibung |
|---|---|
| `GET /api/vms` | Alle VMs auflisten |
| `POST /api/vms` | Neue VM erstellen |
| `GET /api/vms/{id}` | VM-Details |
| `PUT /api/vms/{id}` | VM-Config ändern |
| `DELETE /api/vms/{id}` | VM löschen |
| `POST /api/vms/{id}/start` | VM starten |
| `POST /api/vms/{id}/stop` | VM stoppen (graceful) |
| `POST /api/vms/{id}/pause` | VM pausieren |
| `POST /api/vms/{id}/resume` | VM fortsetzen |
| `POST /api/vms/{id}/reset` | Hard-Reset |
| `GET /api/vms/{id}/status` | Laufzeitstatus |
| `GET /api/vms/{id}/vnc` | VNC-Token generieren |
| `GET /api/vms/{id}/snapshots` | Snapshot-Liste |
| `POST /api/vms/{id}/snapshots` | Snapshot erstellen |
| `DELETE /api/vms/{id}/snapshots/{snap}` | Snapshot löschen |
| `POST /api/vms/{id}/snapshots/{snap}/restore` | Snapshot wiederherstellen |
| `POST /api/vms/{id}/resize` | Disk-Größe ändern |
| `POST /api/vms/{id}/clone` | VM klonen |
| `POST /api/vms/import` | VM-Image importieren |
| `GET /api/vms/isos` | ISO-Liste |
| `POST /api/vms/isos` | ISO hochladen/herunterladen |
| `DELETE /api/vms/isos/{name}` | ISO löschen |

---

## VM-Config-Felder

```json
{
  "id": "uuid",
  "name": "Ubuntu Dev VM",
  "status": "running",
  "cpu_cores": 4,
  "memory_mb": 8192,
  "disk_gb": 50,
  "disk_format": "qcow2",
  "os_type": "linux",
  "network": "bridge",
  "vnc_port": 5901,
  "boot_order": ["hd", "cdrom"]
}
```

---

## VNC-Zugriff

```
GET /api/vms/{id}/vnc
→ {token: "temp-token", url: "wss://host/vnc/token"}

Frontend öffnet noVNC-Client mit Token
→ WebSocket → VNC-Proxy → QEMU VNC-Port
```

---

## systemd-Einschränkung (bekannt)

`hydrahive2.service` hat `DeviceAllow=/dev/kvm` in der systemd-Unit.
Bei `/dev/net/tun`-Bedarf (bridged Netzwerk): Drop-In nötig:
```
/etc/systemd/system/hydrahive2.service.d/tun.conf
[Service]
DeviceAllow=/dev/net/tun rw
DeviceAllow=/dev/vhost-net rw
```

---

## Verwandte Subsysteme

- **→ API** (`04-api.md`): `routes/vms_*.py`
- **→ Extensions** (`25-extensions.md`): VMs können für Extensions genutzt werden
