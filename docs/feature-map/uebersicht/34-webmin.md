# Feature Map: Webmin — Server-Monitoring via RPC

> **Tool-Dateien:** `tools/webmin_status.py`, `tools/webmin_call.py`  
> **Was:** Webmin-Integration via XML-RPC. Agents können Server-Status lesen und Module aufrufen.  
> **Warum:** Homelab-Management — Agents können Systemzustand prüfen ohne ssh.

---

## Architektur

```
Agent ruft webmin_status() auf
  → tools/webmin_status.py
  → webmin/client.py: XML-RPC-Call
  → Webmin-Server (https://homelab:10000/xmlrpc.cgi)
  → Response: CPU, RAM, Disk, Load, Uptime, Processes
  → (Optional) SMART-Temperaturen

Agent ruft webmin_call(module, function) auf
  → tools/webmin_call.py
  → XML-RPC: module::function(args)
  → Beliebige Webmin-Modul-Funktionen
```

---

## Authentifizierung

- Credentials aus Credential-Store (Profil: `webmin`)
- Niemals im Output sichtbar
- Voraussetzung: Webmin-User braucht RPC-Berechtigung
  (Webmin → Webmin Users → User → Allowed modules → 'webmin' → rpc: Yes)

---

## webmin_status — Felder

```python
webmin_status(include_smart=True)
→ {
    "cpu_percent": 12.3,
    "memory": {"total_mb": 32768, "used_mb": 14234, "free_mb": 18534},
    "disk": [
        {"mount": "/", "total_gb": 500, "used_gb": 123, "free_gb": 377}
    ],
    "load_average": [0.45, 0.67, 0.71],
    "uptime_days": 42,
    "process_count": 234,
    "smart_temps": [
        {"device": "/dev/sda", "temp_celsius": 38}
    ]
}
```

---

## webmin_call — Beispiele

```python
# Cron-Jobs auflisten:
webmin_call(module="cron", function="list_cron_jobs")

# Netzwerk-Interfaces:
webmin_call(module="net", function="active_interfaces")

# Prozesse:
webmin_call(module="proc", function="list_processes")

# Installierte Pakete:
webmin_call(module="software", function="list_packages")
```

---

## Dateien

| Datei | Verantwortung |
|---|---|
| `tools/webmin_status.py` | `webmin_status` Tool-Wrapper |
| `tools/webmin_call.py` | `webmin_call` Tool-Wrapper |
| `webmin/client.py` | XML-RPC-Client (Verbindung, Auth, Calls) |
| `webmin/parsers.py` | Response-Parser für verschiedene Module |

---

## Verwandte Subsysteme

- **→ Tools** (`02-tools.md`): `webmin_*` in REGISTRY
- **→ Credentials** (`30-credentials.md`): Webmin-Auth aus Vault
- **→ Plugins** (`10-plugins.md`): `code-metrics`, `git-stats` etc. sind als Plugins implementiert
