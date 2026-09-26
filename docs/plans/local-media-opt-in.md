# Plan: Local Media (ComfyUI) nur noch per Opt-in — Install/Uninstall im System-Fenster

Stand: 2026-09-26 · Task b7616eb7 · Entscheidungen Till (26.09.2026)

## Ziel

Heute installiert `installer/modules/72-local-media.sh` ComfyUI samt ~33 GB
Modellen automatisch, sobald `nvidia-smi` existiert, beim Install **und bei
jedem Update**. Nach diesem Plan gilt:

1. Install und Update richten Local Media **nie mehr von selbst** ein.
2. Im System-Fenster gibt es eine Karte „Lokale Bild-/Videogenerierung“:
   - nicht installiert → Knopf **Installieren**, gesperrt bei zu kleiner oder fehlender GPU
   - installiert → Knopf **Entfernen** (Container, Modelle, Backend-Eintrag)
3. Bestehende Installationen (Workstation) gelten als **eingeschaltet** und werden
   vom Update weiter gepflegt.
4. Auf HydrahiveHome (Quadro P2200, 5 GB) wird ComfyUI über den neuen Weg entfernt.

## Entscheidungen (Till, 26.09.2026)

| Frage | Entscheidung |
|---|---|
| ComfyUI auf HydrahiveHome | entfernen |
| Rechner mit bestehender Installation | als eingeschaltet behandeln |
| Zu kleine Grafikkarte | Installation **sperren** (nicht nur warnen) |
| Nach der Installation | Knopf wechselt auf **Entfernen** |

## Design

### Zustand = eine Marker-Datei

`$HH_CONFIG_DIR/local-media.enabled`, Inhalt = Zeitstempel. Existiert sie,
pflegt das Update Local Media. Sonst passiert nichts. Die Datei schreibt nur
root (Install-/Uninstall-Runner); die GUI stellt nur eine Anfrage.

**Migration (Entscheidung 2):** Das Update legt den Marker einmalig an, wenn
der Rechner **erkennbar schon eingerichtet** ist, also wenn der Docker-Container
`hydra-comfyui` existiert. Die Prüfung stützt sich auf den Container, nicht auf
Modelldateien, weil ein abgebrochener Download sonst als „installiert“ gelten würde.

Ausnahme HydrahiveHome: Dort existiert der Container ebenfalls (seit 26.09.
21:23). Er bekommt also auch den Marker und wird danach über den neuen
Entfernen-Knopf abgebaut. Das ist genau der Weg, den Kunden später auch gehen.

### Mindestanforderung (Entscheidung 3: sperren)

`HH_MEDIA_MIN_VRAM_MIB`, Default **12 000 MiB**. Begründung: Der kleinste
mitgelieferte Workflow (SDXL) läuft laut Kommentar in 72-local-media.sh
auf 16 GiB nur mit `--novram`. Das Videomodell FLF2V 14B (fp8) belegt allein
15 GB. Unter 12 GB ist kein mitgeliefertes Paket sinnvoll nutzbar. Der Wert
ist per ENV übersteuerbar (Fachleute, Tests).

Zusätzlich gilt: freier Platz unter `HH_MEDIA_ROOT` ≥ **40 GB**, bestehend aus
33 GB Modellen, ~7 GB Image und Reserve.

Die Sperre wird **zweimal** geprüft:
- Backend (`/status` liefert `can_install` + `blocked_reason`, `POST /install`
  lehnt mit 409 ab): damit der Knopf gar nicht erst aktiv ist.
- `72-local-media.sh` selbst, bevor Docker/Toolkit/Downloads beginnen: damit
  auch ENV/Installer den Schutz nicht umgehen. Ausnahme: `HH_MEDIA_FORCE=1`.

### Ablauf Install (GUI)

`POST /api/system/local-media/install` → schreibt
`$HH_DATA_DIR/.local_media_request` mit Inhalt `install` →
`hydrahive2-local-media.timer` (5 s) → `hydrahive2-local-media.service`
(root, oneshot) → `installer/local-media-ctl.sh` liest die Anfrage:
- `install`: Marker setzen, dann `72-local-media.sh` ausführen. Schlägt das
  fehl, wird der Marker wieder entfernt, damit das nächste Update nicht erneut
  33 GB anfängt.
- `uninstall`: `72-local-media-uninstall.sh`, danach Marker entfernen.

Log: `/var/log/hydrahive2-local-media.log`, gelesen über `GET …/log`. Am Ende
schreibt das Skript eine eindeutige Abschlusszeile
(`[hh2-media] FERTIG: install ok` / `… FEHLER: …`). Der Dialog wertet diese aus.

Warum ein eigener Runner statt direkt 72-local-media.sh: Die Unit braucht
eine Stelle, die zwischen install und uninstall unterscheidet, und die
Anfrage-Datei darf nur feste Wörter enthalten (keine Pfade oder Parameter aus
der GUI).

### Ablauf Uninstall

`72-local-media-uninstall.sh`:
1. `docker rm -f hydra-comfyui`
2. Backend `local-gpu` aus `llm.json` entfernen, atomar und ohne andere Einträge
   anzufassen. Zeigt ein Standard-Modell (`media_models.image/video`) auf
   `local:local-gpu/…`, wird es geleert, damit HydraHive nicht ins Leere
   generiert.
3. `local-media.env` löschen.
4. `$HH_MEDIA_ROOT` (Modelle + ComfyUI-Daten) löschen. **Schutz:** nur wenn der
   Pfad absolut ist, nicht `/` und eine erwartete Struktur hat (`models/`
   oder `data/`).
5. Docker-Image `yanwk/comfyui-boot:*` entfernen (~7 GB).
6. Docker selbst und das NVIDIA Container Toolkit **bleiben**, weil sie auch
   für andere Extensions gebraucht werden können.

### Install (Neuinstallation) und Update

- `install.sh`: neue Frage im Wizard, `HH_INSTALL_LOCAL_MEDIA`, Default **n**,
  wird in `install.conf` gespeichert. Bei `yes` wird der Marker gesetzt und
  `72-local-media.sh` ausgeführt; ein Fehler ist nur `err_soft`.
- `update.sh`: Migration (siehe oben). Dann `72-local-media.sh` **nur mit Marker**
  und nur mit Warnung bei Fehler, **kein** `err` mehr.
- `72-local-media.sh` bekommt keinen eigenen Marker-Check: Es ist das
  Install-Werkzeug. Wer es direkt aufruft, will installieren.

### Neue systemd-Units

`hydrahive2-local-media.service/.timer` in `50-systemd.sh` (frisch) und als
Nachrüst-Block in `update.sh`. Das stellt `test_update_sh_systemd_units.py`
automatisch sicher.

## Dateien

| Datei | Änderung |
|---|---|
| `installer/modules/72-local-media.sh` | VRAM-/Platz-Sperre, Abschlusszeile |
| `installer/modules/72-local-media-uninstall.sh` | **neu**: Entfernen |
| `installer/local-media-ctl.sh` | **neu**: Runner (install/uninstall, Marker) |
| `installer/modules/50-systemd.sh` | Units anlegen |
| `installer/update.sh` | Migration, Gate, Units nachrüsten, kein `err` |
| `installer/install.sh` | Wizard-Frage, Default nein |
| `core/src/hydrahive/api/routes/system_local_media.py` | **neu**: status/install/uninstall/log |
| `core/src/hydrahive/system/local_media_status.py` | **neu**: GPU/Platz/Installiert ermitteln |
| `core/src/hydrahive/settings/_paths.py` | `local_media_log` |
| `core/src/hydrahive/api/main.py` | Router registrieren |
| `frontend/src/features/system/LocalMediaCard.tsx` | **neu**: Karte |
| `frontend/src/features/system/localMediaApi.ts` | **neu**: API-Aufrufe (api.ts bleibt klein) |
| `frontend/src/features/cockpit/admin/SystemOverlay.tsx` | Karte einbinden |
| `frontend/src/i18n/locales/{de,en}/system.json` | Texte |
| `core/tests/test_local_media_opt_in.py` | **neu**: Shell-Verhalten (echt ausgeführt) |
| `core/tests/test_local_media_api.py` | **neu**: Endpoints |
| `docs/specs/local-media-runtime.md` | „automatisch“ → Opt-in |
| `installer/README.md` | Log + Knopf |

## Reihenfolge (TDD)

1. **Status-Ermittlung** (`local_media_status.py`): Test zuerst für
   GPU fehlt / 5 GB gesperrt / 16 GB ok / Platz zu klein / installiert.
2. **API**: Tests für 401/403, `install` gesperrt → 409, `install` ok → Anfrage-Datei
   mit `install`, `uninstall` nur wenn installiert, Log.
3. **Runner + Uninstall**: Shell wirklich ausführen mit Ersatz-`docker`,
   temporärem Config-/Media-Verzeichnis: Marker gesetzt/entfernt, Backend
   entfernt, andere Backends bleiben, Standard-Modell geleert, Pfad-Schutz greift.
4. **72-local-media.sh-Sperre**: mit Ersatz-`nvidia-smi` (5120 MiB) → Abbruch
   **vor** Docker/Downloads; `HH_MEDIA_FORCE=1` hebt auf.
5. **update.sh**: Gate + Migration + kein `err` (Text-Tests wie bestehende
   `test_update_sh_*`); Units-Parität automatisch.
6. **install.sh**: Wizard-Frage, Default nein, in `CONF_VARS`.
7. **Frontend**: Karte, Dialog, Sperrgrund, Log; `tsc -b`, eslint, build.
8. **Doku**.

Jeder Test wird per Gegenprobe gegen den alten Stand geprüft.

## Akzeptanzkriterien

- [ ] Update auf Rechner mit NVIDIA, **ohne** Marker und ohne Container: kein
      Docker, kein Download, keine Änderung an llm.json.
- [ ] Update auf Rechner **mit** `hydra-comfyui`: Marker wird angelegt, Runtime
      wird wie bisher aktualisiert.
- [ ] Fehler in 72-local-media.sh bricht das Update nicht ab.
- [ ] GUI bei 5-GB-Karte: Knopf gesperrt, Grund sichtbar; API lehnt ab (409).
- [ ] Install über GUI → Log live → Karte zeigt „installiert“ + Entfernen.
- [ ] Entfernen → Container, Image, Modelle, Backend-Eintrag und Marker weg;
      andere Backends/Einstellungen unverändert.
- [ ] Nächstes Update nach Entfernen installiert **nichts** neu.
- [ ] pytest, ruff, `tsc -b`, eslint, vite build grün; CI grün.

## Nicht in diesem Plan

- Compute-Node (`node-agent/scripts/setup.sh` ruft setup-local-media.sh
  ebenfalls automatisch auf) → eigener Folgeschritt im Sammel-Task d9c9516f.
- Auswahl einzelner Modellpakete (nur Bild / nur Video).
- Docker/NVIDIA-Toolkit deinstallieren.
