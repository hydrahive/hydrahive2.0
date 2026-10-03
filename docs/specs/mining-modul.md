# Spec: Mining-Modul — GPU-Rechner im Netz für Kryptex verwalten

**Stand:** 2026-10-03 · **Status:** Design, Aufbau von Till freigegeben, noch nicht implementiert
**Verwandt:** `node-agent/` (Kopplungsmuster), `docs/specs/compute-cluster-v1.md`,
Modul `homeassistant` (spätere Energiequelle möglich)

---

## Was

Ein HydraHive-Modul `mining` plus ein kleiner Client `hydrahive-rig` für
Ubuntu-/Debian-Rechner mit **einer** Grafikkarte (NVIDIA oder AMD). HydraHive
verwaltet bis zu **20 Rechner**. Es misst einmal pro Rechner, wie schnell die
Karte bei jedem Algorithmus ist, rechnet mit den Live-Daten von Kryptex aus,
welcher Coin für **diesen** Rechner gerade am meisten bringt, und lässt den
Rechner darauf schürfen. Ausgezahlt wird über **ein** Kryptex-Konto.

## Warum

Der Einsatz ist für einen Betreiber mit eigener PV-Anlage gedacht. Strom und
Hardware zählen deshalb nicht, es zählt allein der Ertrag. Bei uns läuft das
Modul nur zum Testen. Vorbild für die Funktionen ist RainbowMiner (GPL-3.0,
PowerShell, für Windows gebaut). **Es wird kein Code übernommen.**

## Verifizierte Grundlagen (03.10.2026)

| Was | Befund |
|---|---|
| Kryptex-API | offen, ohne Schlüssel, OpenAPI unter `pool.kryptex.com` |
| `/api/v1/index` | 30 Coins, davon 11 mit `device_types: gpu` (s. u.) |
| `/{coin}/api/v1/pool/info` | `estimated_profit_day` = Coin je H/s und Tag; Gegenrechnung für RVN: 1,8 Mio. RVN Tagesausschüttung / 650 GH/s ≈ 2,8e-6, Kryptex nennt 2,4e-6 → Einheit plausibel |
| Kurs | `/api/v1/coin/{coin}/price/chart?time_range=day` in USD; stimmt mit CoinGecko auf < 2 % überein |
| Stratum | z. B. `rvn-eu.kryptex.network:7031` (SSL 8031), Login `benutzername/worker` oder `wallet/worker` |
| Worker-Daten | `/{coin}/api/v3/miner/workers/{address}`, `miner/balance/{address}`; **ob `address` den Benutzernamen annimmt, ist ungeprüft** (E4) |
| Miner (Linux) | Rigel 1.23.2 (nur NVIDIA), SRBMiner-Multi 3.7.1 (AMD+NVIDIA), lolMiner 1.98a (AMD+NVIDIA). Alle sind Closed Source und behalten 0,85–2 % Gebühr ein |
| Test-Hardware | wks197: Ubuntu 26.04, Python 3.14, RTX 5060 Ti 16 GB, Treiber 595.91; erreicht hydratest (.217) und Kryptex. **Keine AMD-Karte vorhanden** |
| HydraHive | Modul-Router hängen fest hinter `require_capability("module.<id>")`, also hinter einem Nutzer-Login. Für Geräte ohne Nutzer gibt es keinen Weg (→ E0) |

**GPU-Coins bei Kryptex und Miner-Abdeckung** (aus Miner-Doku/RainbowMiner, je Coin in E3 auf wks197 zu prüfen):

| Coin | Algo | Gebühr Pool | NVIDIA | AMD |
|---|---|---|---|---|
| iron | FishHash | 1 % | Rigel, SRB, lolMiner | SRB, lolMiner |
| rvn, xna, quai-kawpow | KawPow | 1 % | Rigel, SRB | SRB |
| erg | Autolykos2 | 1 % | Rigel, SRB, lolMiner | SRB, lolMiner |
| cfx | Octopus | 1 % | Rigel, lolMiner | lolMiner |
| nexa | NexaPow | 3 % | Rigel | – |
| xel | XelisHash v3 | 1 % | Rigel, SRB | SRB |
| prl | PearlHash | 2 % | SRB | SRB |
| xtm-c29, qtc | Cuckaroo29, Poseidon2 | 1–3 % | nicht in V1 (Miner-Unterstützung unklar) | |

## Aufbau

```
 HydraHive (Modul mining)                         Rig (hydrahive-rig, systemd)
 ├─ Kryptex-Abruf (Job, alle 5 min)                ├─ meldet alle 30 s: Karte, Temp,
 ├─ Rechner: Ertrag je Rig × Coin                  │   Watt, Hashrate, Miner-Zustand
 ├─ Entscheider: Soll-Zustand je Rig  ◄── HTTPS ───┤   (nur ausgehend, kein offener Port)
 ├─ Energie-Steuerung (Schnittstelle)  ──────────► ├─ bekommt Soll-Zustand zurück
 └─ Oberfläche + Agent-Werkzeuge                   └─ startet/stoppt/misst Miner, Watchdog
```

**Soll-Zustand statt Befehle:** Die Antwort auf jede Meldung ist der gewünschte
Zustand (`stop` | `benchmark <algo>` | `mine <coin, algo, miner, pool>`). Der
Client gleicht ab. Fällt eine Antwort aus, passiert nichts Doppeltes.

### E0 — Kern: Geräte-Zugang für Module (Core-PR)

`ctx.register_device_router(router, auth=<dependency>)` hängt den Router unter
`/api/modules/<id>/device` **ohne** Nutzer-Login ein. Der Kern erzwingt dabei die
übergebene Prüfung als Dependency, das Modul kann sie also nicht vergessen.
Ohne `auth` lehnt der Kern ab. `min_core_version` des Moduls steigt entsprechend.

Verworfen wurden: Nutzer-API-Keys pro Rig (zu viele Rechte, kommen an Chat und
Agenten heran); ein eigener Dienst mit eigenem Port (zusätzlicher Port, TLS und
Proxy); der Compute-Kanal (mTLS und signierte Jobs, fest auf Incus zugeschnitten
und Teil des Kerns).

### E1 — Modul-Grundgerüst + Ertragstabelle

- Kryptex-Abruf als `register_job` (alle 5 min) mit Cache. Bei einem Ausfall
  bleiben die letzten Werte stehen, gekennzeichnet als „veraltet seit …“.
- Ertrag/Tag = `estimated_profit_day × Hashrate × Kurs`. Rechnung in USD, Anzeige
  zusätzlich in EUR (EZB-Tageskurs).
- Seite „Mining“ mit Coin-Tabelle. Ohne gemessene Rechner werden Referenzwerte
  angezeigt, gekennzeichnet als Schätzung.
- Einstellungen: Kryptex-Benutzername, Region (EU/…), Wechselschwelle,
  Mindestlaufzeit.

### E2 — Client: Koppeln + Melden

- Paket `mining/rig/` im Modul-Repo, nur mit `httpx` als Abhängigkeit, Python ≥ 3.11
  (Debian 12 / Ubuntu 24.04+). Installiert wird mit
  `sudo sh setup.sh --server … --code … --pin …`: eigener Systemnutzer `hh-rig`
  (Gruppen `video`, `render`), venv, systemd-Dienst.
- **Koppeln:** Der Admin klickt auf „Rechner koppeln“ und bekommt den fertigen
  Befehl mit Einmal-Code (≥ 10 Zeichen, 15 min gültig, einmalig) und dem
  Fingerabdruck des Server-Zertifikats. Damit funktionieren auch
  selbstsignierte Zertifikate sicher. Der Rig tauscht den Code gegen ein
  eigenes Token (Datei `0600` beim Rig, nur der Hash auf dem Server).
  Danach steht er auf **„wartet auf Freigabe“**, bis der Admin ihn freigibt.
  Widerruf wirkt sofort.
- GPU-Erkennung: NVIDIA über `nvidia-smi`, AMD über sysfs (`/sys/class/drm`) und,
  wenn vorhanden, `rocm-smi`. Fehlt der Treiber oder die OpenCL-/CUDA-Laufzeit,
  meldet der Rig das als klaren Fehler, statt einfach zu schweigen.
- Kopplungs-Endpunkt mit Rate-Limit.

### E3 — Miner verwalten + Messen

- Miner-Katalog als Daten im Modul: Miner, Version, Download-URL (offizielle
  GitHub-Releases), **SHA-256**, unterstützte Algos je Hersteller, Aufruf-Vorlage.
  Der Rig startet nur Dateien, deren Hash passt, und nur Pools unter
  `*.kryptex.network`.
- **Benchmark:** beim ersten Freigeben, bei einem Wechsel von Treiber oder Miner
  und auf Knopfdruck. Jeder Algo läuft ca. 3 min echt gegen den Pool (also nicht
  verschenkt). Gespeichert werden Hashrate und Watt je Rig × Algo × Miner.
  Pro Algo zählt der schnellste Miner.
- **Watchdog:** Stirbt der Miner oder liegt die Hashrate > 3 min bei 0, wird
  neu gestartet. Nach 3 Fehlschlägen in Folge geht es zum nächstbesten Coin
  weiter, und es gibt eine Meldung in HydraHive.
- Bricht die Verbindung zum Server ab: weiterschürfen (Standard). Ist die
  Energie-Steuerung aktiv, nach 15 min stoppen, sonst würde ohne PV Netzstrom
  verbraucht.

### E4 — Automatisch umschalten + Erträge

- Entscheidung je Rig: bester Coin nach `Ertrag/Tag` aus eigener Messung.
  Gewechselt wird nur, wenn ein anderer Coin **≥ 5 %** mehr bringt **und** der
  aktuelle seit **≥ 15 min** läuft (beides einstellbar). Jeder Wechsel kommt mit
  Grund ins Protokoll.
- PROP-Coins (Auszahlung schwankt) bekommen einen einstellbaren Abschlag
  gegenüber PPS+.
- Ist-Erträge und Worker-Status aus der Kryptex-Worker-API; Worker-Name =
  Rig-Name.
- Agent-Werkzeuge: `mining_status` (lesen), `mining_set_rig` (an/aus,
  Capability `mining.control`).

### E5 — Energie-Steuerung (PV vorbereitet, zu- und abschaltbar)

Die PV-Anlage ist ein Eigenbau und wird später angebunden. Jetzt wird nur die
**Schnittstelle** gebaut:

- Schalter **„Energie-Steuerung“: Aus** (Standard, alle freigegebenen und
  eingeschalteten Rigs laufen) **| Fester Wert** (z. B. „max. 2.000 W“, gut zum
  Testen) **| Quelle** (später).
- Quellen-Schnittstelle `PowerSource.available_watts() -> float | None`. Weitere
  Quellen kommen nur über eine neue Klasse dazu, z. B. „HTTP-JSON“
  (URL + Feld, passt zu einem Eigenbau), „Home Assistant“ (Sensor über das
  vorhandene Modul) oder MQTT. `None` bedeutet: Quelle nicht erreichbar, dann
  gilt das Verhalten „Verbindung weg“ von oben.
- Verteilung: Rigs nach **Ertrag je Watt** sortiert (das ist nur hier relevant),
  eingeschaltet wird, solange die **gemessenen** Watt ins Budget passen,
  abzüglich einer Reserve (Standard 100 W). Gegen Flattern bei Wolken: ein Rig
  bleibt mindestens 10 min an bzw. aus.
- Je Rig: Schalter „folgt Energie-Steuerung“ und eine Priorität.

## Datenmodell (Modul-Migrationen)

`mining_rigs` (id, name, status pending|active|disabled, token_hash, OS,
gpu_vendor/model/mem, driver, client_version, enabled, follows_power,
priority, last_seen) · `mining_pairing_codes` (code_hash, name, expires_at,
used_at) · `mining_benchmarks` (rig, algo, miner, miner_version, hashrate,
watts, measured_at) · `mining_rig_state` (rig, coin, algo, miner, hashrate,
watts, temp, fan, since, error) · `mining_profit_cache` (coin, profit_per_hs,
price_usd, fetched_at) · `mining_switch_log` (rig, von, nach, Grund, Zeit).

## Sicherheit

- Das Rig-Token kann nur melden und Soll-Zustände abholen. Kein Nutzerzugang,
  keine Agenten, keine Dateien.
- Der Server kann keine freien Befehle schicken, nur die drei Zustände. Binaries
  laufen nur mit passendem Hash, Pools nur aus der Allowlist.
- Der Kryptex-Benutzername ist kein Geheimnis. Es gibt keine Wallet-Schlüssel,
  keine Auszahlungsfunktion und keinen Login bei Kryptex.
- Capabilities: `module.mining` (ansehen, Standard admin_only), `mining.control`
  (koppeln, schalten, Einstellungen, admin_only).

## Akzeptanzkriterien

1. E0: Device-Router ohne `auth` wird abgelehnt; mit `auth` ist er ohne Login
   erreichbar, aber mit falschem Token → 401. Andere Modul-Router bleiben
   unverändert geschützt (Tests).
2. E1: Die Coin-Tabelle zeigt Live-Werte von Kryptex. Bei Kryptex-Ausfall:
   letzte Werte mit Hinweis, kein Fehler 500.
3. E2: wks197 lässt sich an hydratest koppeln, erscheint nach Freigabe als
   „online“ mit RTX 5060 Ti. Widerruf → nächste Meldung 401. Token taucht in
   keinem Log auf.
4. E3: Benchmark läuft für alle NVIDIA-Algos der Tabelle; falscher Hash → Miner
   startet nicht; abgeschossener Miner wird neu gestartet.
5. E4: Wechsel nur bei ≥ Schwelle und nach Mindestlaufzeit (Tests mit
   künstlichen Kursen); Worker taucht bei Kryptex unter dem Rig-Namen auf.
6. E5: Mit „Fester Wert 0 W“ stoppen alle folgenden Rigs, mit „Aus“ laufen sie
   wieder; kein Flattern innerhalb der Mindestzeit (Tests).

## Nicht-Ziele (V1)

Mehrere GPUs pro Rig · Übertakten/Spannung (Power-Limit nur später, braucht
root) · Windows/HiveOS · MiningRigRentals/NiceHash-Vermietung · Pools außer
Kryptex · die eigentliche PV-Quelle · Auszahlungen auslösen.

## Offene Punkte

- Ein Kryptex-Konto (Benutzername) für den Test auf wks197. Vor E3 nötig.
- AMD kann bei uns nur mit Unit-Tests geprüft werden. Der echte Test läuft beim
  Betreiber.
- Root auf wks197 für die Installation als Systemdienst (einmalig `sudo`).
  Alternative zum Testen: Client im Nutzerkontext ohne systemd.
