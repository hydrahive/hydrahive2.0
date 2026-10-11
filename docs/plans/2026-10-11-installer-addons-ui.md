# Plan: Zusatz-Module über die Oberfläche nachinstallieren (installer-core-first, Teil 2)

Spec: `docs/specs/installer-core-first.md` §3 (freigegeben 11.10.2026). Task a594de49.

## Bausteine

1. **`installer/addon-ctl.sh`** (root, Muster `local-media-ctl.sh`)
   - Liest `$HH_DATA_DIR/.addon_request`: genau eine Zeile `install <modul>`.
   - Positivliste: `containers vms samba whatsapp voice tailscale`. Alles andere: `FEHLER: unbekannte Anfrage verworfen`, Exit 2.
   - `voice` → vorher `containers`, falls `incus` fehlt.
   - Ruft das Modul-Skript mit `HH_INSTALL_<X>=yes` auf. **Nur bei Erfolg** `hh_conf_set install.conf HH_INSTALL_<X> yes`.
   - Logzeilen `[hh2-addon] ===== … =====`, `FERTIG: install <modul> ok`, `FEHLER: …`.
   - Trigger wird am Ende entfernt (`trap`), auch bei Fehlern.
   - Skript-Pfade über ENV (`HH_REPO_DIR`), damit Tests mit Ersatz-Modulen in tmp laufen.
2. **systemd** `hydrahive2-addon.service` + `.timer` (Muster Local Media) in `50-systemd.sh` und als Self-Heal in
   `update.sh`. Log `/var/log/hydrahive2-addon.log`.
3. **API** `core/src/hydrahive/api/routes/system_addons.py` (nur Admin) + `core/src/hydrahive/system/addons_status.py`
   - `GET /api/system/addons` → Liste `{id, installed, enabled, running, restarts_service, hint}` + `running` (global).
   - `POST /api/system/addons/{id}/install` → 202 `{started}`; 409 `addon_busy` bei laufendem Auftrag; 400 `addon_unknown`;
     409 `addon_installed` falls schon installiert.
   - `GET /api/system/addons/log?tail=` (ANSI entfernt, max. 1000).
   - `enabled` aus install.conf (nur lesen; Datei ist 600 hydrahive → lesbar für den Dienst).
   - `hint`: WSL erkannt → bei vms/containers/voice „wsl“.
4. **Alte Wege umleiten** (eine Version lang):
   - `POST /api/system/install-voice` → schreibt `install voice` in `.addon_request` (Antwort unverändert `{started}`).
   - `POST /api/system/samba/setup` → `install samba` (Passwortdatei-Anlage bleibt).
   - `POST /api/tailscale/install` → `install tailscale`, Antwort `{ok, rc, output, status, started}` bleibt kompatibel;
     `tailscale/install.py` (sudo -n bash) entfällt.
   - Alte Trigger-Units (voice/samba) bleiben liegen (Bestand), werden nur nicht mehr beschrieben.
5. **Oberfläche**: `features/system/AddonsCard.tsx` + `useAddons.ts` + `addonsApi.ts` (Muster LocalMediaCard)
   - Zeile je Modul: Name, Nutzen, Status, Knopf „Installieren“ → Rückfrage (VMs/Container: Neustart-Hinweis).
   - Log ausklappbar, Polling während Lauf; nach Dienst-Neustart weiter pollen.
   - Kopf-Knopf „Voice installieren“ + `VoiceInstallModal`/`useVoiceInstall` entfallen.
   - Tailscale-Karte: Installieren-Knopf startet Runner, zeigt Log-Ende (über `/system/addons/log`).
   - i18n de/en.
6. **Doku**: `installer/README.md` Abschnitt „Zusatz-Module nachinstallieren“.

## Tests (TDD, je zuerst rot)
- `test_addon_ctl.py`: echtes bash, Ersatz-Modul-Skripte in tmp-Repo; Positivliste, unbekannt/leer/Injection verworfen,
  install.conf nur bei Erfolg, voice zieht containers, Trigger weg nach Lauf, Log-Zeilen.
- `test_addons_api.py`: Admin-only, Liste, 202/409/400, Log, Status gemockt.
- `test_addons_status.py`: Zustandsprüfungen gemockt, enabled aus install.conf, WSL-Hinweis.
- `test_addon_units.py`: 50-systemd.sh und update.sh legen Units an (statisch wie test_update_sh_systemd_units).
- Umleitungen: voice/samba/tailscale schreiben `.addon_request`.
- vitest: AddonsCard (Status, Knopf gesperrt bei Lauf, Neustart-Hinweis bei vms).

## Prüfung
Volle Suite, ruff/shellcheck, Mutanten, vitest/tsc/eslint, Gegenprobe main, hh-instcore Browser-Klickweg
(Container, Samba, WhatsApp, VMs + 409), hydratest Bestand (Karte zeigt alles installiert), PR, CI, Tills OK.
