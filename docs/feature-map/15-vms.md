# VMs

> Subsystem: lokales QEMU/KVM-VM-Management im Core von HydraHive2.
> **Wichtige Klarstellung vorweg:** Das VM-Subsystem nutzt **kein incus und kein
> libvirt**. Es spricht `qemu-system-x86_64` / `qemu-img` als rohe Subprozesse
> an (kein `shell=True`, alles als argv-Liste). „incus/libvirt" gehören zum
> **Container-Subsystem** (`containers/`), das in SPEC.md als „Schwester von VMs"
> beschrieben ist (`SPEC.md:561-582`) — siehe Abschnitt „Offene Enden / Abgrenzung".
> SPEC sagt explizit: „ohne Proxmox- oder libvirt-Zwischenschicht" (`SPEC.md:528`).

---

## WAS

### Backend-Module (`core/src/hydrahive/vms/`)

- `vms/__init__.py` — **leer** (0 Zeilen). Kein Re-Export; Submodule werden direkt importiert (`from hydrahive.vms import db as vmdb` etc.).
- `vms/models.py` — Dataclasses + Typ-Literals + Limits-Konstanten.
  - `VM` Dataclass (alle 24 Felder, inkl. `disk_interface`, `machine_type`, `network_device`, `project_id`).
  - `ISO` Dataclass (filename / size_bytes / sha256 / uploaded_at).
  - `Snapshot` Dataclass (snapshot_id / vm_id / name / created_at / description / size_bytes).
  - `ImportJob` Dataclass (job_id / owner / source_path / target_qcow2 / status / progress_pct / bytes_done / bytes_total / error_code / created_at / finished_at).
  - Typ-Literals: `DesiredState` (`running|stopped`), `ActualState` (`created|starting|running|stopping|stopped|error`), `NetworkMode` (`bridged|isolated`), `ImportStatus` (`queued|running|done|failed`), `DiskInterface` (`virtio|sata|ide`), `MachineType` (`q35|pc`), `NetworkDevice` (`virtio-net-pci|e1000`).
  - Tuples für Validierung: `DISK_INTERFACES`, `MACHINE_TYPES`, `NETWORK_DEVICES`.
  - Limit-Konstanten: `MIN_CPU=1`, `MAX_CPU=16`, `MIN_RAM_MB=256`, `MAX_RAM_MB=65536`, `MIN_DISK_GB=1`, `MAX_DISK_GB=1024`, `NAME_RE = ^[a-zA-Z][a-zA-Z0-9-]{0,31}$` (1-32 Zeichen, Buchstabe vorn).
- `vms/db.py` — CRUD für `vms`-Tabelle. Funktionen: `create_vm`, `get_vm`, `list_vms`, `delete_vm`, `set_project`, `list_for_project`, `clear_project_assignments`, `name_taken`, `used_vnc_ports`, plus Re-Export von `update_vm_state`/`update_vm_config`. Row→Dataclass-Mapping `_row_to_vm` mit defensivem `keys()`-Check für nachträglich migrierte Spalten.
- `vms/_vms_db_updates.py` — Partial-Update-Helpers `update_vm_state` (Lifecycle/Reconciler) und `update_vm_config` (Edit-Route). Sentinel-Pattern `...` = nicht ändern, `None` = explizit NULL setzen.
- `vms/qemu_args.py` — Baut argv-Liste für `qemu-system-x86_64` aus VM-Konfig. Funktionen: `build_qemu_args`, `_disk_args`, `_iso_drive_path`, `_mac_for`, `ensure_dirs`, `qcow2_create_args`.
- `vms/lifecycle.py` — start/stop/poweroff via QEMU-Subprozess. `start`, `shutdown`, `_read_pid`, `_pid_alive`, `_tail`, Exception `VMLifecycleError`.
- `vms/disk.py` — qcow2-Disk-Erzeugung/-Resize via `qemu-img`. `disk_path_for`, `create_qcow2`, `remove_qcow2`, `grow_qcow2`, Exception `DiskError`.
- `vms/iso.py` — ISO-Upload/-Validierung/-Listing. `safe_filename`, `validate_iso9660`, `save_upload_stream`, `_hash_file`, `list_isos`, `_iso_mtime`, `delete_iso`, Exception `ISOError`. Konstanten `ISO9660_MAGIC=b"CD001"`, `ISO9660_OFFSET=32768`, `MAX_ISO_BYTES=8 GiB`, `SAFE_NAME_RE`.
- `vms/snapshots.py` — qcow2-Snapshots via `qemu-img snapshot` (offline-only) + DB-Funktionen. `validate_name`, `_qemu_img`, `create`, `restore`, `delete`, `_parse_size`, `db_create`, `db_list`, `db_get`, `db_delete`, Exception `SnapshotError`. Konstante `SNAPSHOT_NAME_RE = ^[a-zA-Z0-9_.-]{1,64}$`.
- `vms/import_job.py` — Disk-Image-Import (qcow2/raw/vmdk/vdi/vhd/vhdx/vpc → qcow2). `detect_format`, `run_convert`, `execute_job`, Exception `ImportError_`. Re-Export der DB-Funktionen. Konstanten `SUPPORTED_FORMATS`, `PROGRESS_RE`.
- `vms/_import_job_db.py` — DB-Zugriff Import-Jobs. `db_create_job`, `db_update`, `db_list`, `db_get`, `db_delete`.
- `vms/ports.py` — VNC-Port-Allocator. `allocate_vnc_port`, `_port_in_use`. Konstante `VNC_PORT_RANGE = range(5900, 6000)` (100 Slots).
- `vms/vnc.py` — VNC-Token-Files für websockify. `_safe_token`, `write_token`, `remove_token`, `cleanup_orphans`.
- `vms/reconciler.py` — Reconciliation-Loop (actual_state ↔ Realität). `_pid_alive`, `reconcile_once`, `run_loop`. Konstanten `POLL_INTERVAL_S=3.0`, `ACTIVE_STATES=("running","starting","stopping")`.
- `vms/stats.py` — Live-Stats aus `/proc/<pid>` (kein QMP). `read_stats`, `forget`. Modul-State `_LAST`, Konstanten `_CLK_TCK`, `_NUM_CPUS`.

### API-Endpoints (alle unter Prefix `/api/vms`, Tag `vms`, alle `Depends(require_auth)`)

Lifecycle/CRUD (`vms_lifecycle.py`):
- `GET  /api/vms` — eigene VMs listen (Admin sieht alle). → `list[dict]`.
- `POST /api/vms` (201) — VM erstellen (Boot-Quelle: ISO / Import-Job / blank). Validiert Name, network_mode, disk_interface, machine_type, network_device, name_taken; legt qcow2 an oder verschiebt importierte Disk hinein.
- `GET  /api/vms/{vm_id}` — VM-Detail.
- `PATCH /api/vms/{vm_id}` — VM-Konfig ändern (nur im stopped/created/error-State); Disk nur vergrößerbar (offline grow), ISO setzen/clearen.
- `DELETE /api/vms/{vm_id}` (204) — VM löschen (force-shutdown bei running, qcow2 mitgelöscht).

Runtime-Ops (`vms_ops.py`):
- `POST /api/vms/{vm_id}/start` — QEMU starten.
- `POST /api/vms/{vm_id}/stop` — graceful Shutdown (SIGTERM/ACPI).
- `POST /api/vms/{vm_id}/poweroff` — harter Shutdown (SIGKILL).
- `GET  /api/vms/{vm_id}/stats` — Live-CPU%/RSS/Uptime aus /proc.
- `GET  /api/vms/{vm_id}/log?tail=N` — QEMU-Log-Tail (1..2000 Zeilen, Default 200).

Snapshots (`vms_snapshots.py`, alle offline = VM muss stopped sein):
- `GET    /api/vms/{vm_id}/snapshots` — Snapshots listen.
- `POST   /api/vms/{vm_id}/snapshots` (201) — Snapshot erstellen (name 1-64, description ≤500).
- `POST   /api/vms/{vm_id}/snapshots/{snapshot_id}/restore` (204) — Snapshot wiederherstellen.
- `DELETE /api/vms/{vm_id}/snapshots/{snapshot_id}` (204) — Snapshot löschen.

Import-Jobs (`vms_imports.py`):
- `GET    /api/vms/import-jobs` — Import-Jobs listen (eigene; Admin alle).
- `POST   /api/vms/import-jobs/upload` (202) — Disk-Image hochladen + Convert als BackgroundTask.
- `POST   /api/vms/import-jobs/from-path` (202) — **admin-only**: Server-seitigen Pfad importieren (Source bleibt stehen, `cleanup_source=False`).
- `DELETE /api/vms/import-jobs/{job_id}` (204) — Import-Job löschen (qcow2 nur gelöscht wenn von keiner VM benutzt).

ISO-Library (`vms_isos.py`):
- `GET    /api/vms/isos/list` — ISOs listen (ohne Hash, schnell).
- `POST   /api/vms/isos/upload` (201) — ISO hochladen + ISO-9660-Magic-Validierung.
- `DELETE /api/vms/isos/{filename}` (204) — **admin-only**: ISO löschen.

VNC (`vms_vnc.py`):
- `GET    /api/vms/{vm_id}/vnc` — VNC-Token + ws_path (`/vnc-ws/`) für noVNC. 409 wenn VM nicht running / kein Token.

### Externe Konsumenten der VM-DB (kein eigener vms-Endpoint)

- `GET /api/projects/{project_id}/servers` (`projects_servers.py:25`) — listet zugewiesene VMs+Container.
- `GET /api/projects/{project_id}/servers/available` (`:39`) — VMs ohne Projekt-Zuweisung.
- `POST /api/projects/{project_id}/servers/assign` (`:58`) — VM einem Projekt zuweisen (`vms_db.set_project`).
- `DELETE /api/projects/{project_id}/servers/{kind}/{server_id}` (`:89`) — Zuweisung lösen (`set_project(None)`).
- `GET /api/dashboard` (`dashboard.py:41-65`) — VMs in Server-Übersicht + `servers_running`-Zähler.

### Frontend (`frontend/src/features/vms/`)

UI-Komponenten:
- `VMsPage.tsx` — Hauptseite (Route `/vms`), Polling alle 4 s, Summary-Cards, VM-Grid, Modal-Orchestrierung. Lokale `SummaryCard`.
- `VMCard.tsx` — VM-Kachel mit Live-Stats-Polling (3 s wenn running), Specs, Error-Anzeige, Delete-Confirm.
- `_VMCardActions.tsx` — Button-Leiste (Start/Console/Stop/Poweroff/Logs/Snapshots/Edit/Delete).
- `StatusBadge.tsx` — farbiges Status-Badge mit Pulse-Animation für starting/stopping. `PRESETS`-Map.
- `CreateVMDialog.tsx` — Erstell-Dialog (Boot-Quelle iso/import/blank, Slider für CPU/RAM/Disk, Radio-Cards für Netz/Disk-Interface/Machine-Type/Network-Device).
- `EditVMDialog.tsx` — Edit-Dialog (nur wenn editable=stopped/created/error; Disk nur vergrößern; ISO/Interface/Machine/NIC ändern); eigenes lokales `Field`.
- `_vmDialogHelpers.tsx` — geteilte `Field`, `Slider`, `RadioCard`.
- `_vmHelpers.tsx` — `Bar`, `Spec` (Stats-Balken + Spec-Pill).
- `VMConsoleModal.tsx` — noVNC-Konsole (`@novnc/novnc` RFB), Ctrl+Alt+Del, Fullscreen, `StatusPill`.
- `SnapshotsPanel.tsx` — Slide-over-Panel: Snapshots listen/erstellen/restore/delete.
- `ImportJobsPanel.tsx` — Slide-over-Panel: Upload (XHR-Progress) + From-Path + Job-Liste, Polling 2 s.
- `_ImportJobCard.tsx` — einzelne Import-Job-Kachel mit Progress-Bar. `STATUS_CLS`-Map.
- `ISOLibraryPanel.tsx` — Slide-over-Panel: ISO-Upload (XHR-Progress) + Liste + Delete.
- `VMLogsPanel.tsx` — Slide-over-Panel: QEMU-Log-Viewer, Auto-Refresh-Toggle (2.5 s), Auto-Scroll.
- `novnc.d.ts` — TypeScript-Ambient-Deklaration für `@novnc/novnc` (RFB-Klasse).

Datenschicht:
- `api.ts` — `vmsApi`-Objekt (alle Endpoints) + `uploadImport` + `uploadIso` (beide XHR statt fetch für Upload-Progress).
- `types.ts` — TS-Spiegel der Dataclasses (`VM`, `ISO`, `Snapshot`, `ImportJob`, `VMCreateInput` + Typ-Unions).
- `format.ts` — `formatBytes`, `formatRamMB`, `formatRelative` (relative Zeit, **hardcoded Deutsch**: „gerade eben", „vor X min").

i18n:
- `i18n/locales/en/vms.json`, `i18n/locales/de/vms.json` — Namespace `vms` (title/status/actions/iso/imports/snapshots/logs/create/edit).

### Config-Flags / Env-Vars

- `HH_VMS_BRIDGE` (Env) — Bridge-Name, Default `br0` (`settings/_infra.py:54`).
- `HH_INSTALL_VMS` (Installer-Env) — `no` überspringt VM-Setup (`installer/modules/65-vms.sh:14`).
- VM-Verzeichnisse alle abgeleitet aus `data_dir/vms` (keine eigenen Env-Vars, siehe Datenmodell).

### Installer / Infra

- `installer/modules/65-vms.sh` — installiert qemu-system-x86/qemu-utils/bridge-utils/websockify/novnc, setuid auf qemu-bridge-helper, `/etc/qemu/bridge.conf` (`allow br0`), kvm-Gruppe, systemd-Patches (`DeviceAllow=/dev/kvm`, `DeviceAllow=/dev/net/tun`, `SupplementaryGroups=kvm`), websockify-Service.
- `installer/setup-bridge.sh` — legt br0-Bridge via netplan an (separat wegen SSH-Kill-Risiko).
- `installer/modules/60-nginx.sh:117-126` — nginx `location /vnc-ws/` → `127.0.0.1:6080` (WebSocket-Upgrade).

---

## WIE

### VM erstellen (POST /api/vms)
Klick „New VM" → `CreateVMDialog` → `vmsApi.create()` → `POST /api/vms` (`vms_lifecycle.py:40`):
1. Validierung der Reihe nach: `NAME_RE`, network_mode ∈ {bridged,isolated}, disk_interface ∈ DISK_INTERFACES, machine_type ∈ MACHINE_TYPES, network_device ∈ NETWORK_DEVICES, dann `name_taken(user, name)` → 409.
2. `resolve_iso(body.iso_filename)` (`_vms_helpers.py:35`) — sanitisiert zum Basename, prüft Existenz in `vms_isos_dir`.
3. `resolve_import_job(body.import_job_id,...)` (`_vms_helpers.py:47`) — prüft Owner/Admin, Status `done`, qcow2 existiert; gibt Pfad zurück.
4. `vmdb.create_vm(...)` legt DB-Zeile mit `qcow2_path=""`, `desired='stopped'`, `actual='created'` an.
5. Disk-Beschaffung im try/except:
   - Mit Import-Job: `shutil.move(import_qcow2 → disk_path_for(vm_id))`, dann `vmimport.db_delete(job_id)`.
   - Sonst: `await vmdisk.create_qcow2(vm_id, disk_gb)` (sparse qcow2 via `qemu-img create`).
   - Bei `DiskError`/`OSError`: **Rollback** `vmdb.delete_vm(vm.vm_id)`, dann 500.
6. Roher `UPDATE vms SET qcow2_path=?` (direkter `_db()`-Zugriff, **umgeht** `update_vm_config`).
7. `serialize(get_vm(...))` → 201.

### VM starten (POST /{id}/start → lifecycle.start)
`vms_ops.py:22` → `lifecycle.start(vm_id)` (`lifecycle.py:27`):
1. `ensure_dirs()` legt alle vms_*-Dirs an.
2. `get_vm`; **idempotent**: bei actual_state ∈ {running,starting} sofort return.
3. `Path(qcow2_path).exists()`-Check → `qcow2_missing`.
4. `allocate_vnc_port()` (`ports.py:24`) — erster freier Port aus 5900-5999 (DB-bekannt + System-frei via `bind`-Probe); None → `vnc_ports_exhausted`.
5. `secrets.token_urlsafe(24)` als VNC-Token.
6. `update_vm_state(desired='running', actual='starting', vnc_port, vnc_token, error=None)`.
7. `build_qemu_args(vm, port)` → argv.
8. QEMU als Daemon (`-daemonize`) via `asyncio.create_subprocess_exec`, stdout/stderr → `vms_logs_dir/{vm_id}.log` (append). `wait()` mit Timeout 20 s.
   - `FileNotFoundError` → state=error `qemu_system_missing`.
   - rc≠0 → state=error `qemu_start_failed` mit log_tail (letzte 20 Zeilen).
   - `TimeoutError` → state=error `qemu_daemonize_timeout`.
9. PID aus Pidfile lesen (`_read_pid`); `_pid_alive`-Check → sonst `qemu_died_after_start`.
10. **Erst jetzt** `vnc.write_token(token, port)` (vorher würde websockify auf toten Port routen). Fehler beim Token nur als Warning geloggt.
11. `update_vm_state(actual='running', pid)`.

### VM stoppen (stop/poweroff → lifecycle.shutdown)
`lifecycle.shutdown(vm_id, hard=)` (`lifecycle.py:88`):
1. Wenn pid None oder tot: Token entfernen, state=stopped, return.
2. `update_vm_state(desired='stopped', actual='stopping')`.
3. `os.kill(pid, SIGKILL if hard else SIGTERM)` (ProcessLookupError ignoriert).
4. Warte-Loop: bis 20× 0.5 s (graceful) bzw. 5× 0.5 s (hard) auf pid-Tod, für UX-Feedback. Reconciler räumt den Rest.
5. `vnc.remove_token`, `update_vm_state(actual='stopped', pid=None, vnc_port=None, vnc_token=None)`.

### Reconciliation (Background-Loop, alle 3 s)
`reconciler.run_loop` (gestartet in `lifespan.py:130-131`) → `reconcile_once` (`reconciler.py:36`):
1. `list_vms(owner=None)` (alle).
2. Für jede VM mit actual_state ∈ ACTIVE_STATES:
   - `_pid_alive(pid)` true + Token → Token zu `active_tokens` hinzu, continue.
   - Prozess tot → `new_state = 'error' if desired=='running' else 'stopped'`; bei error `error_code='qemu_process_died'`. `update_vm_state(actual=..., pid=None, vnc_port=None, vnc_token=None)`, `vnc.remove_token`.
3. `vnc.cleanup_orphans(active_tokens)` — Token-`.cfg`-Files ohne lebende VM löschen.
Stop via Event in `lifespan.py:220` (`vm_reconciler_stop.set()`).

### qemu_args-Aufbau (`build_qemu_args`, `qemu_args.py:27`)
- KVM-Detect: `Path("/dev/kvm").exists()` → cpu_model `host`/`qemu64`, machine accel `kvm`/`tcg`. Bei TCG bewusst **kein** `-cpu max` (emuliert AES-NI/SHA-NI buggy → FreeBSD libcrypto crash).
- Basis-argv: `-name hh2-<name>`, `-machine <type>,accel=...`, `-cpu`, `-smp`, `-m`, `-pidfile`, `-qmp unix:<vm_id>.qmp,server=on,wait=off`, `-display vnc=127.0.0.1:<port-5900>`, `-rtc base=utc,clock=host`, `-device virtio-balloon`, `-device virtio-rng-pci`, `-daemonize`.
- `_disk_args`: virtio (if=virtio,cache=writeback,discard=unmap) / sata (AHCI + ide-hd) / ide (if=ide,cache=writeback, **kein discard** wegen FreeBSD-gptzfsboot-IRQ-Race).
- ISO: nur via `_iso_drive_path` (real + unter vms_isos_dir → sonst None). Mit ISO: `-drive media=cdrom,readonly=on` + `-boot order=dc,menu=on`. Ohne: `-boot order=c,menu=on`.
- Netzwerk: bridged → `-netdev bridge,br=<vms_bridge>` + NIC; isolated → `-netdev user,restrict=yes` (blockt Internet). MAC stabil aus vm_id (`_mac_for`, Prefix `52:54:00`).

### Import-Job (`execute_job`, `import_job.py:103`, BackgroundTask)
1. `db_get(job_id)`; `status='running'`.
2. `src.exists()`-Check → `import_source_missing`.
3. `detect_format(src)` via `qemu-img info --output=json`; Format muss in SUPPORTED_FORMATS sein.
4. **Wenn qcow2**: `shutil.copy2` 1:1 (Original-Layout bit-genau, kein convert — sonst zerstört es FreeBSD-gptzfsboot durch cluster_size/subformat-Wechsel). `progress_pct=100`.
5. **Sonst**: `run_convert` (`qemu-img convert -p -f <fmt> -O qcow2`), Progress aus stdout via `PROGRESS_RE` geparst, `db_update(progress_pct=...)`.
6. Erfolg → `status='done', progress_pct=100, finished_at`. Fehler → `status='failed', error_code`, dst gelöscht.
7. `finally`: bei `cleanup_source=True` (Upload) wird src gelöscht; bei from-path (`cleanup_source=False`) bleibt sie.

### ISO-Upload (`save_upload_stream`, `iso.py:52`)
Stream in 1-MiB-Chunks, parallel sha256 + Größenzähler (Cap 8 GiB → `iso_too_large`), nach Abschluss `validate_iso9660` (liest Magic „CD001" bei Byte 32769). Bei Fehler dst gelöscht. Filename via `safe_filename` (Basename, Sonderzeichen→`_`, `.iso`-Suffix erzwungen).

### VNC-Konsole (Browser)
Klick „Console" → `VMConsoleModal` → `vmsApi.vncInfo(id)` → `GET /{id}/vnc` liefert `{token, ws_path:"/vnc-ws/"}`. Frontend baut `wss://host/vnc-ws/?token=<token>`, öffnet `RFB`. nginx proxied `/vnc-ws/` → websockify `127.0.0.1:6080`. websockify liest `<token>.cfg` aus `vms_vnc_tokens_dir` (Inhalt `<token>: 127.0.0.1:<vnc_port>`) und proxied auf den lokalen VNC-Port.

### Live-Stats (`stats.read_stats`, `stats.py:23`)
Liest `/proc/<pid>/stat` (utime+stime ticks, starttime) und `/proc/<pid>/status` (VmRSS). CPU-% = Δticks/Δt/CLK_TCK, normiert auf vCPUs. Letzter Snapshot pro vm_id im Modul-State `_LAST` (in-memory, bei Backend-Restart reset). Erster Aufruf liefert cpu_pct=0.

### Disk-Resize (offline grow)
`PATCH` mit größerer disk_gb → `grow_qcow2(vm_id, new)` (`disk.py:49`) via `qemu-img resize` **bevor** DB-Update (Konsistenz). Verkleinern blockiert (`vm_disk_shrink_not_supported`). Gast muss FS danach selbst vergrößern (growpart/resize2fs — UI-Hinweis).

---

## WO

### Backend-Module
- VM-Dataclass + Limits: `core/src/hydrahive/vms/models.py:19` (VM), `:46` (ISO), `:54` (Snapshot), `:64` (ImportJob), `:79-86` (Limits/NAME_RE).
- DB: `core/src/hydrahive/vms/db.py:20` `_row_to_vm`, `:39` `create_vm`, `:61` `get_vm`, `:67` `list_vms`, `:79` `delete_vm`, `:84` `set_project`, `:92` `list_for_project`, `:101` `clear_project_assignments`, `:108` `name_taken`, `:122` `used_vnc_ports`.
- Partial-Updates: `core/src/hydrahive/vms/_vms_db_updates.py:10` `update_vm_state`, `:37` `update_vm_config`.
- qemu_args: `core/src/hydrahive/vms/qemu_args.py:13` `_iso_drive_path`, `:27` `build_qemu_args`, `:82` `_disk_args`, `:112` `_mac_for`, `:118` `ensure_dirs`, `:125` `qcow2_create_args`.
- Lifecycle: `core/src/hydrahive/vms/lifecycle.py:20` `VMLifecycleError`, `:27` `start`, `:88` `shutdown`, `:113` `_read_pid`, `:121` `_pid_alive`, `:129` `_tail`.
- Disk: `core/src/hydrahive/vms/disk.py:11` `DiskError`, `:18` `disk_path_for`, `:22` `create_qcow2`, `:44` `remove_qcow2`, `:49` `grow_qcow2`.
- ISO: `core/src/hydrahive/vms/iso.py:22` `ISOError`, `:29` `safe_filename`, `:40` `validate_iso9660`, `:52` `save_upload_stream`, `:97` `list_isos`, `:121` `delete_iso`.
- Snapshots: `core/src/hydrahive/vms/snapshots.py:24` `SnapshotError`, `:31` `validate_name`, `:53` `create`, `:70` `restore`, `:77` `delete`, `:84` `_parse_size`, `:103` `db_create`, `:116` `db_list`, `:125` `db_get`, `:133` `db_delete`.
- Import-Job: `core/src/hydrahive/vms/import_job.py:43` `ImportError_`, `:54` `detect_format`, `:75` `run_convert`, `:103` `execute_job`. DB: `core/src/hydrahive/vms/_import_job_db.py:8` `db_create_job`, `:21` `db_update`, `:30` `db_list`, `:42` `db_get`, `:48` `db_delete`.
- Ports: `core/src/hydrahive/vms/ports.py:11` `_port_in_use`, `:24` `allocate_vnc_port`, Range `:8`.
- VNC: `core/src/hydrahive/vms/vnc.py:19` `_safe_token`, `:26` `write_token`, `:35` `remove_token`, `:42` `cleanup_orphans`.
- Reconciler: `core/src/hydrahive/vms/reconciler.py:26` `_pid_alive`, `:36` `reconcile_once`, `:72` `run_loop`.
- Stats: `core/src/hydrahive/vms/stats.py:23` `read_stats`, `:84` `forget`, State `:17`.

### API-Routen
- Aggregator: `core/src/hydrahive/api/routes/vms.py:24-32` (Sub-Router-Includes, **Reihenfolge!**).
- Lifecycle/CRUD: `core/src/hydrahive/api/routes/vms_lifecycle.py:33` GET list, `:40` POST create, `:95` GET detail, `:101` PATCH update, `:161` DELETE.
- Schemas: `core/src/hydrahive/api/routes/_vm_lifecycle_schemas.py:10` `VMCreate`, `:24` `VMUpdate`.
- Helpers: `core/src/hydrahive/api/routes/_vms_helpers.py:18` `is_admin`, `:22` `vm_or_404`, `:31` `serialize`, `:35` `resolve_iso`, `:47` `resolve_import_job`.
- Ops: `core/src/hydrahive/api/routes/vms_ops.py:22` start, `:32` stop, `:39` poweroff, `:46` stats, `:52` log.
- Snapshots: `core/src/hydrahive/api/routes/vms_snapshots.py:18` `SnapshotCreate`, `:23` list, `:29` create, `:45` restore, `:62` delete.
- Imports: `core/src/hydrahive/api/routes/vms_imports.py:24` `ImportFromPath`, `:28` list, `:34` upload, `:70` from-path, `:92` delete.
- ISOs: `core/src/hydrahive/api/routes/vms_isos.py:17` list, `:22` upload, `:36` delete.
- VNC: `core/src/hydrahive/api/routes/vms_vnc.py:18` vnc_info.
- Router-Include in App: `core/src/hydrahive/api/main.py:65` import, `:128` `app.include_router(vms_router)`.
- Reconciler-Start/Stop: `core/src/hydrahive/api/lifespan.py:35` import, `:130-131` Task-Start, `:220` Stop, `:225` shutdown_tasks.

### Settings / DB-Schema / Installer
- VM-Pfade: `core/src/hydrahive/settings/_infra.py:28-55` (`_VmsMixin`).
- Migrationen: `core/src/hydrahive/db/migrations/003_vms.sql` (vms/vm_snapshots/vm_import_jobs), `008_vm_disk_interface.sql`, `009_vm_machine_network.sql`, `005_project_assignments.sql:7,10` (project_id+Index).
- Installer: `installer/modules/65-vms.sh`, `installer/setup-bridge.sh`, `installer/modules/60-nginx.sh:117-126`.

### Externe Konsumenten
- `core/src/hydrahive/api/routes/projects_servers.py:20,32,49,67,74,99,104`.
- `core/src/hydrahive/api/routes/dashboard.py:16,41,60-62`.
- `core/src/hydrahive/projects/config.py:113,120` (`clear_project_assignments` beim Projekt-Löschen).

### Frontend
- `frontend/src/App.tsx:21` Import, `:75` `<Route path="vms" .../>`.
- `frontend/src/features/vms/*` (alle oben gelisteten Dateien).
- i18n: `frontend/src/i18n/locales/{en,de}/vms.json`.

### Tests
- `core/tests/test_vms_route_order.py` — literale Pfade vor `/{vm_id}` (Regression).
- `core/tests/test_vm_iso_traversal.py` — Path-Traversal-Schutz (Issue #179).
- `core/tests/test_import_qcow2_passthrough.py` — qcow2 1:1-Copy statt convert.
- `core/tests/test_vm_disk_interface.py`, `core/tests/test_vm_machine_network.py`.

---

## WARUM

- **Route-Reihenfolge ist load-bearing** (`vms.py:7-11`): FastAPI matcht in Definitionsreihenfolge; `import-jobs`/`isos`-Router müssen VOR `lifecycle`-Router (mit `/{vm_id}`) included werden, sonst landet `GET /api/vms/import-jobs` in `vm_or_404("import-jobs")` → 404. Genau dieser Bug existierte real (Test `test_vms_route_order.py`). **Wenn du Include-Reihenfolge in `vms.py` umstellst, brechen Import-Jobs/ISO-Panels stumm.**
- **desired_state vs. actual_state**: `desired` = User-Wille (running/stopped), `actual` = letzter Reconciler-Messwert. Der Reconciler entscheidet bei totem Prozess `error` (wenn desired=running, „unerwartet gestorben") vs. `stopped` (wenn desired=stopped, „erwartet"). Invariante: Frontend zeigt IMMER die Realität, auch nach Crash/kill -9/Reboot.
- **Token-Schreiben erst nach running-Bestätigung** (`lifecycle.py:78-81`): Würde websockify sonst auf einen toten VNC-Port routen. Reihenfolge ist Absicht.
- **VNC-Port-Allocator macht doppelten Check** (`ports.py`): DB-bekannte Ports + echter `bind`-Probe — fängt Ports, die von Nicht-HH-Prozessen gehalten werden. Race: zwischen Allocate und QEMU-Bind kann ein anderer Prozess den Port klauen (kein Lock) → QEMU-Start scheitert dann mit `qemu_start_failed`.
- **qcow2-Import = 1:1-Copy, kein convert** (`import_job.py:121-125`): `qemu-img convert` ändert cluster_size + subformat (qcow2-v3). FreeBSDs gptzfsboot ist gegen Layout-Wechsel empfindlich → „ZFS I/O error"/„no bootable disks". Frische Installation funktioniert (gleiche Args), nur der Import-Pfad brach das Image. **Wenn du den qcow2-Zweig auf convert umstellst, brechen importierte BSD-Images.**
- **disk_interface/machine_type/network_device existieren wegen Boot-Kompatibilität** (Migrationen 008/009): hartes virtio+q35 brach FreeBSD-ZFS-Boot („cannot read MOS") und importierte VBox/VMware-Images ohne virtio-Treiber („no bootable device"). Defaults bleiben modern (virtio/q35/virtio-net-pci); User wählt sata/pc/e1000 für Imports.
- **ide-Interface bewusst ohne `discard=unmap`** (`qemu_args.py:99-104`): IDE hat kein TRIM, und FreeBSD-gptzfsboot bekommt bei IRQ-Race I/O-Errors.
- **Kein `-cpu max` unter TCG** (`qemu_args.py:33-38`): emuliert AES-NI/SHA-NI buggy → FreeBSD-libcrypto-Crash. `qemu64` ist konservativ.
- **Path-Traversal Defense-in-Depth (Issue #179)**: (1) `update_vm`/`create_vm` speichern nur den sanitisierten Basename via `resolve_iso` (NICHT den Rohwert), (2) `_iso_drive_path` mountet nur ISOs, deren resolved Pfad real unter `vms_isos_dir` liegt. Selbst wenn ein roher `../../etc/passwd` in die DB käme, wird er nicht als CD-ROM gemountet. **Beide Schichten müssen bleiben** — Test deckt beide ab.
- **Snapshot-Token / VNC-Token nur URL-safe** (`vnc.py:_safe_token`, `snapshots.py:SNAPSHOT_NAME_RE`): verhindert Path-Tricks in Dateinamen.
- **Snapshots offline-only**: `qemu-img snapshot` braucht eine nicht-laufende Disk. Live-Snapshots bräuchten QMP savevm/loadvm — bewusst nicht gebaut (Docstring `snapshots.py:3-5`). Alle Snapshot-Routen prüfen `actual_state == "stopped"`.
- **systemd-DeviceAllow-Falle** (`65-vms.sh:73-80`, Issue #176): Sobald die erste `DeviceAllow=`-Direktive gesetzt ist, läuft die Unit im Whitelist-Modus → `/dev/net/tun` ist gesperrt (EPERM trotz korrekter Bridge + setuid). Deshalb muss `/dev/net/tun` explizit erlaubt werden, sonst funktioniert bridged Networking nicht.
- **br0 wird NICHT vom Installer angelegt** (`65-vms.sh:6-9`): Netzwerk-Reconfig kann laufende SSH killen → separates `setup-bridge.sh`, das netplan-Renderer (networkd vs. NetworkManager, Issue #174) korrekt wählt.
- **qcow2_path-Update umgeht `update_vm_config`** (`vms_lifecycle.py:88-91`): bewusster Roh-UPDATE, weil `update_vm_config` kein qcow2_path-Feld hat. Wer den Create-Flow anfasst, muss das Roh-SQL beachten.
- **Create-Rollback** (`vms_lifecycle.py:81-87`): Bei Disk-Fehler wird die schon angelegte VM-Zeile sofort gelöscht — sonst bleiben Geister-VMs mit `qcow2_path=""` zurück, die beim Start `qcow2_missing` werfen.
- **Stats-State ist in-memory** (`stats.py:_LAST`): nach Backend-Restart zeigt CPU% beim ersten Tick 0. Kein Persistenz-Bedarf (UI pollt eh alle 3 s).

---

## Datenmodell

### Tabelle `vms` (Migration 003 + 005/008/009)
| Spalte | Typ | Notiz |
|---|---|---|
| vm_id | TEXT PK | uuid7 |
| owner | TEXT NOT NULL | Per-User-Isolation |
| name | TEXT NOT NULL | NAME_RE, unique pro owner (App-Level, kein DB-UNIQUE) |
| description | TEXT | |
| cpu | INTEGER NOT NULL | 1-16 |
| ram_mb | INTEGER NOT NULL | 256-65536 |
| disk_gb | INTEGER NOT NULL | 1-1024, nur vergrößerbar |
| iso_filename | TEXT | nur sanitisierter Basename |
| network_mode | TEXT DEFAULT 'bridged' | bridged/isolated |
| qcow2_path | TEXT NOT NULL | leer bei Create, dann Roh-UPDATE |
| disk_interface | TEXT DEFAULT 'virtio' | Migration 008 — virtio/sata/ide |
| machine_type | TEXT DEFAULT 'q35' | Migration 009 — q35/pc |
| network_device | TEXT DEFAULT 'virtio-net-pci' | Migration 009 — virtio-net-pci/e1000 |
| desired_state | TEXT DEFAULT 'stopped' | running/stopped |
| actual_state | TEXT DEFAULT 'created' | created/starting/running/stopping/stopped/error |
| pid | INTEGER | QEMU-PID |
| vnc_port | INTEGER | 5900-5999 |
| vnc_token | TEXT | secrets.token_urlsafe(24) |
| last_error_code | TEXT | i18n-Key fürs Frontend |
| last_error_params | TEXT | JSON |
| project_id | TEXT | Migration 005, NULL bei Projekt-Löschen |
| created_at / updated_at | TEXT NOT NULL | ISO |

Indizes: `idx_vms_owner`, `idx_vms_actual_state`, `idx_vms_project`.

### Tabelle `vm_snapshots` (Migration 003)
`snapshot_id` PK, `vm_id` FK (ON DELETE CASCADE), `name`, `description`, `size_bytes`, `created_at`. Index `idx_snapshots_vm`.
**Achtung:** Snapshot existiert in der qcow2 (qemu-img) UND als DB-Zeile — zwei Wahrheiten, siehe Offene Enden.

### Tabelle `vm_import_jobs` (Migration 003)
`job_id` PK, `owner`, `source_path`, `target_qcow2`, `status` (queued/running/done/failed), `progress_pct`, `bytes_done` (**nie befüllt**), `bytes_total`, `error_code`, `created_at`, `finished_at`. Indizes `idx_import_jobs_owner`, `idx_import_jobs_status`.

### Config-Keys (`settings/_infra.py`, alle cached_property)
- `vms_dir` = `data_dir/vms`
- `vms_isos_dir` = `vms_dir/isos`
- `vms_disks_dir` = `vms_dir/disks`
- `vms_pids_dir` = `vms_dir/pids` (auch `.qmp`-Sockets)
- `vms_logs_dir` = `vms_dir/logs`
- `vms_vnc_tokens_dir` = `vms_dir/vnc-tokens`
- `vms_bridge` = Env `HH_VMS_BRIDGE` || `br0`
- Import-Temp: `vms_dir/imports-tmp` (kein Settings-Property; hardcoded in `import_job._imports_tmp` UND `vms_imports.py` — siehe Offene Enden)

### Wichtige Konstanten
- `VNC_PORT_RANGE = range(5900, 6000)`, nginx/websockify auf `127.0.0.1:6080`.
- `ISO9660_MAGIC=b"CD001"`, `ISO9660_OFFSET=32768`, `MAX_ISO_BYTES=8 GiB`.
- `SUPPORTED_FORMATS = {qcow2, raw, vmdk, vdi, vhd, vhdx, vpc}` (Import erkennt mehr als die UI bewirbt).
- `POLL_INTERVAL_S=3.0` (Reconciler).
- MAC-Prefix `52:54:00` (QEMU locally-administered).

### Error-Codes (Auswahl, alle i18n-Keys)
`vm_not_found`, `vm_no_access`, `vm_name_invalid`, `vm_name_taken`, `vm_network_mode_invalid`, `vm_disk_interface_invalid`, `vm_machine_type_invalid`, `vm_network_device_invalid`, `vm_must_be_stopped`, `vm_disk_shrink_not_supported`, `vm_iso_not_found`, `vm_not_running`, `qcow2_missing`, `qcow2_exists`, `qcow2_create_failed`, `qcow2_resize_failed`, `qemu_system_missing`, `qemu_img_missing`, `qemu_start_failed`, `qemu_daemonize_timeout`, `qemu_died_after_start`, `qemu_process_died`, `vnc_ports_exhausted`, `iso_invalid_name`, `iso_invalid_format`, `iso_read_failed`, `iso_already_exists`, `iso_too_large`, `iso_not_found`, `import_source_missing`, `import_format_unknown`, `import_format_unsupported`, `import_convert_failed`, `import_internal_error`, `import_upload_failed`, `import_move_failed`, `import_job_not_found`, `import_job_not_done`, `import_qcow2_missing`, `snapshot_name_invalid`, `snapshot_create_failed`, `snapshot_restore_failed`, `snapshot_delete_failed`, `snapshot_vm_not_stopped`, `snapshot_not_found`.

### Events
**Keine.** Das VM-Subsystem emittiert keine HH-Events/Trigger. SPEC.md:557 listet zwar `events`/`errors` als geplante Module — die existieren nicht. Frontend pollt (4 s Liste, 3 s Stats, 2 s Imports, 2.5 s Logs).

---

## Offene Enden

- **„incus/libvirt-Backend" gibt es im VM-Subsystem NICHT.** VMs = rohe QEMU-Subprozesse. incus ist das **Container**-Subsystem (`containers/`, SPEC.md:561-582). Wer hier ein incus/libvirt-Backend erwartet, sucht im falschen Modul.
- **SPEC-Drift bei geplanten Modulen** (`SPEC.md:556-557`): SPEC nennt `events` und `errors` als VM-Submodule — **existieren nicht**. Error-Handling läuft über Exceptions + `last_error_code`-DB-Feld; Events fehlen ganz.
- **`bytes_done` wird nie geschrieben**: Spalte existiert in `vm_import_jobs` + ImportJob-Dataclass, aber kein Code setzt sie je. Progress läuft nur über `progress_pct`. Tote Spalte.
- **`imports-tmp`-Pfad doppelt definiert (DRY-Bruch)**: `import_job._imports_tmp()` (`import_job.py:50`) gibt `vms_dir/imports-tmp` zurück — wird aber nirgends aufgerufen. Die Route `vms_imports.py:43` baut den Pfad selbst neu (`settings.vms_dir / "imports-tmp"`). Zwei Quellen für denselben Pfad, kein Settings-Property. `_imports_tmp` ist toter Code.
- **Job-ID-Schema-Mismatch (potenziell verwirrend)**: `vms_imports.py:46,81` erzeugt einen String `import-<millis>` als Teil des **Dateinamens**, der DB-`job_id` ist aber das uuid7 aus `db_create_job` (`_import_job_db.py:10`). Der `import-<millis>`-String landet nur im `source_path`/`target_qcow2`-Dateinamen, NICHT als job_id. Funktioniert, ist aber leicht fehlzulesen.
- **Snapshot-Drift-Risiko**: Snapshot lebt sowohl in der qcow2 (qemu-img) als auch als DB-Zeile. Wird die qcow2 extern manipuliert (oder ein Snapshot per qemu-img gelöscht), driftet die DB. Kein Reconciler für Snapshots (anders als VM-State).
- **VNC-Port-Race**: zwischen `allocate_vnc_port()` und QEMU-Bind kein Lock — bei parallelem Start zweier VMs theoretisch Doppelvergabe (selten, aber möglich).
- **Disk-Resize-Halbzustand**: `grow_qcow2` läuft vor dem DB-Update — gut. Aber wenn die VM mehrere Felder ändert und grow scheitert, ist die qcow2 evtl. schon vergrößert (qemu-img resize ist nicht atomar gegenüber dem DB-Write). Praktisch unkritisch, da grow idempotent wäre.
- **`update_vm_config` kennt kein qcow2_path** → Create-Flow nutzt Roh-SQL (`vms_lifecycle.py:88-91`). Inkonsistenz: ein direkter `conn.execute` mitten im Route-Code statt über die db-Schicht.
- **`format.ts:formatRelative` hardcoded Deutsch** („gerade eben", „vor X min/h/d") — ignoriert i18n, obwohl der Rest des Subsystems `react-i18next` nutzt. Auch viele `confirm()`/`alert()`-Strings in den Komponenten sind hartes Deutsch (z. B. `VMCard.tsx:95`, `SnapshotsPanel.tsx:53,90`, `EditVMDialog.tsx:51,81,89,114-168`, `VMConsoleModal.tsx:83,101`).
- **MEMORY-Notiz**: Laut Audit (`project_review_open_findings_2026_05_28`) ist die Infra-Schicht inkl. `vms/` als „Runde 2 / ungeprüft" markiert — d. h. dieses Subsystem hatte noch kein tiefes Review wie der Agent-Kern.
- **Test-Lücken**: getestet sind nur Route-Order, ISO-Traversal, qcow2-Passthrough, disk_interface, machine/network. **Nicht** getestet: `lifecycle.start/shutdown` (QEMU-Subprozess), Reconciler-Loop, VNC-Token-Lifecycle, Snapshots-Routen, Stats-Berechnung, Port-Allocator-Race. Deutlich unter den 80%-Coverage-Regeln.
- **`from-path`-Import ist admin-only**, Upload aber für jeden User — bewusste Asymmetrie (Server-FS-Zugriff = höheres Risiko), aber nirgends als Invariante dokumentiert außer im Code (`vms_imports.py:76`).
- **noVNC-Passwort leer** (`VMConsoleModal.tsx:30`): `credentials: { password: "" }` — der VNC-Server läuft ohne Passwort, Zugriffsschutz kommt allein vom websockify-Token + Auth-Layer davor. Wer den Token kennt, hat ungeschützten Framebuffer-Zugriff.
