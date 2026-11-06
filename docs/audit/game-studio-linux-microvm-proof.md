# Game Studio PR 0 — Linux-VM-Nachweis für Godot

**Ausgeführt:** 2026-11-06T00:36:52Z
**Ergebnis:** BESTANDEN
**Ausführungsort:** ausdrücklich freigegebene separate HydraHive-Testumgebung
**Source-Digest:** `sha256:7261061eb777d44665b2e8081fc6ebed575064c9ed1dc152b4d4fc07e5b7f87a`

**Maschinenlesbare Evidenz:**

- [`game-studio-pr0-result.json`](evidence/game-studio-pr0-result.json)
- [`game-studio-pr0-proof.pck`](evidence/game-studio-pr0-proof.pck)
- [`game-studio-pr0-proof.png`](evidence/game-studio-pr0-proof.png)

## 1. Aussage und Grenze

Dieser Nachweis belegt, dass ein Godot-Projekt ausschließlich in einer frischen Incus/KVM-VM mit eigenem Kernel, abgeschaltetem Gastnetzwerk, positiv gelistetem Environment und festen Ressourcenlimits validiert, exportiert und gestartet werden kann.

PR 0 beweist noch nicht den späteren vollständigen `game-runtime/v1`-Provider, Core-Projektrollen, signierte Game-Job-Envelopes oder einen produktiven End-to-End-Cancelkanal. Diese bleiben getrennte TDD-Schritte in PR 1–4. Eine echte projektübergreifende Autorisierungsprobe benötigt Core-Projekte und gehört ebenfalls dorthin.

## 2. Reproduzierbare Belegkette

### 2.1 Versionierte Bestandteile

- `node-agent/game_microvm_contract.py` — Policy, Positivliste und feste Limits;
- `node-agent/game_microvm_runtime.py` — begrenzte Incus-/Gastsonden;
- `node-agent/game_microvm_harness.py` — Godot, Cancel, Timeout und VM-Cleanup;
- `node-agent/tests/build_game_microvm_image.sh` — temporärer Imagebuilder;
- `node-agent/tests/run_game_microvm_proof.py` — einziger positiver Evidenzgenerator;
- `node-agent/tests/test_game_runtime_microvm_smoke.py` — Unit-/Negativvertrag und Belegketten-Test;
- `node-agent/tests/fixtures/game_runtime_godot/` — sichtbares Referenzprojekt.

Der Source-Digest umfasst diese Dateien sowie den korrigierten Incus-Netzwerkadapter. Der normale Testlauf überspringt den Infrastrukturtest bewusst; ein Skip oder Mock erzeugt weder `proof_mode=real-incus-kvm` noch Ergebnisdateien.

### 2.2 Godot-Provenienz

- offizielles Releaseasset:
  `https://github.com/godotengine/godot/releases/download/4.4.1-stable/Godot_v4.4.1-stable_linux.x86_64.zip`
- Assetgröße: `62,203,199` Bytes
- lokal berechneter ZIP-SHA-256:
  `d6e382fb531019f85630c1f485a561a0d20c4a2344b6c3847735cfee7da812aa`
- lokal berechneter SHA-256 der entpackten Binärdatei:
  `54215149d52efb1d653a3dec39d0993587bdf5daa2c56e787b5ee88417fb1339`
- Binärversion im Gast: `4.4.1.stable.official.49a5bc7b6`

Das Upstream-Release stellt für dieses Binär-ZIP keine separate veröffentlichte Prüfsummendatei und keinen GitHub-Asset-Digest bereit. Der lokal berechnete Hash wird daher nicht als Upstream-Signatur ausgegeben. Builder, Proof-Konfiguration, Policy-Digest und Ergebnis binden jedoch exakt denselben Hash; eine Abweichung stoppt fail-closed.

### 2.3 Image-Provenienz

| Merkmal | Wert |
|---|---|
| Source-Image-Fingerprint | `c5deab9e0a8245c2b85f20b374de08cfb385d7ac9506c095f4d0ed2923652e33` |
| Paketmanifest-SHA-256 | `5e87ce518df6c5441d9655b0df53727169c5227dec3c13edacc0e857a369b19a` |
| finales Proof-Image | `875b3a82a618ec6bc5585abfe517fb0318a25e99d6a4c644ca1f9ad55cd0cc29` |
| Policy-Digest | `sha256:fe593f948c0c77f0ce8eb8bea6a535f4d1aff7cfd056dc47518de804f1781aad` |

Nur die Builder-VM erhielt vorübergehend das vorhandene Bridge-Netz. Vor `publish` prüfte das Skript die Abwesenheit von `eth0`. Das veröffentlichte Image trägt Source-Image-, Paketmanifest- und Godot-Digest als Incus-Image-Properties. Der Proof verlangte den exakten finalen Fingerprint und startete die VM mit `eth0.type=none`.

Das Image wurde nach dem positiven Lauf durch den Evidenzgenerator gelöscht und seine Abwesenheit geprüft (`image_cleanup_confirmed=true`).

### 2.4 Reproduktion

```bash
cd node-agent

HH_GAME_GODOT_BINARY=/absoluter/pfad/Godot_v4.4.1-stable_linux.x86_64 \
HH_GAME_GODOT_SHA256=54215149d52efb1d653a3dec39d0993587bdf5daa2c56e787b5ee88417fb1339 \
HH_GAME_IMAGE_ALIAS=hh-game-proof-godot-4.4.1 \
HH_GAME_BUILDER_BRIDGE=br0 \
sh tests/build_game_microvm_image.sh

HH_GAME_MICROVM_TEST=1 \
HH_GAME_MICROVM_IMAGE=hh-game-proof-godot-4.4.1 \
HH_GAME_MICROVM_FINGERPRINT=<fingerprint-aus-builder> \
HH_GAME_GODOT_BINARY=/absoluter/pfad/Godot_v4.4.1-stable_linux.x86_64 \
HH_GAME_GODOT_SHA256=54215149d52efb1d653a3dec39d0993587bdf5daa2c56e787b5ee88417fb1339 \
HH_GAME_PROOF_OUTPUT=/absoluter/ausgabeordner \
HH_GAME_PROOF_DELETE_IMAGE=1 \
PYTHONPATH="$PWD/src" \
python3 tests/run_game_microvm_proof.py
```

Der Generator schreibt das JSON atomar erst nach bestätigtem VM-Cleanup und löscht anschließend das lokale Proof-Image. Bei fehlendem Opt-in, Digest, KVM, Incus, Godot oder Cleanup entsteht keine positive Evidenz.

## 3. Plattform und Isolation

| Merkmal | Gemessener Wert |
|---|---|
| Runtime / Virtualisierung | `incus-vm` / `kvm` |
| Incus | Client/Server `6.0.5` |
| QEMU | `10.2.1` |
| Hostkernel | `7.0.0-42-generic` |
| Gastkernel | `6.8.0-147-generic` |
| Gastinterfaces | ausschließlich `lo` |
| Default-Routen | keine |
| DNS / Metadatenroute | nicht verfügbar |
| Hostgeräte / zusätzliche Disks | keine |
| Host-Mounts | nicht sichtbar |
| Docker-/Incus-Sockets | nicht sichtbar |
| Host-Secret-Sentinel | nicht sichtbar |
| Gast-Environment | exakt `HOME`, `LANG`, `PATH`, `USER` |

Die unterschiedlichen Kernel und der gemessene Incus-Typ `virtual-machine` belegen eine eigene Kernelgrenze. Ein Shared-Kernel-Container war nicht beteiligt.

## 4. Ressourcen- und Prozessgrenzen

| Grenze | Wirksamer Wert / Nachweis |
|---|---|
| CPU | `limits.cpu=2` |
| RAM | `limits.memory=2048MiB` |
| Root-Disk | `10GiB` |
| Output | tmpfs `64MiB`, `128` Inodes, `nodev,nosuid,noexec` |
| Dateianzahl | hart durch 128 Output-Inodes, zusätzlich Postcondition `max_files=128` |
| Godot-Prozesse | systemd-Units mit `TasksMax=256` |
| Godot-Laufzeit | systemd-Units mit `RuntimeMaxSec=180s` |
| Hostausgabe | Incus stdout+stderr zusammen maximal `256KiB`; Überschreitung beendet den Clientprozess |

### Cancel-Probe

Ein markierter Kindprozess lief in einer Unit mit `TasksMax=256`. Die VM wurde über den vorhandenen Node-Adapter gestoppt und neu gestartet. Danach waren Unit und markierter Prozess nicht mehr vorhanden. Dies belegt das VM-Stop-Teardown-Primitiv, nicht bereits den späteren Core-Cancelkanal.

### Timeout-Probe

Eine separate Unit lief mit `RuntimeMaxSec=2s` und einem wartenden Kindprozess. systemd beendete den Prozess automatisch mit Nicht-Null-Status innerhalb der Frist; der Markerprozess war anschließend nicht vorhanden. Die VM wurde für diese Probe nicht manuell gestoppt.

### Finaler Cleanup

`run_proof()` löschte die Test-VM mit Retry und exakter Existenzprüfung. Der Real-Run-Generator löschte danach das Image und prüfte dessen Abwesenheit:

```json
{
  "cleanup_confirmed": true,
  "image_cleanup_confirmed": true
}
```

Zusätzlich wurde auf dem Testhost geprüft, dass keine `hh-game-proof-*`-Instanz und kein Proof-Image verblieb.

## 5. Godot-Evidenz

Der Gast führte nacheinander aus:

1. Projektvalidierung im begrenzten Godot-Workload;
2. PCK-Export;
3. Start des exportierten PCK über Xvfb und Mesa llvmpipe/OpenGL;
4. Engine-eigener Movie Writer mit festem FPS und `--quit-after 2`;
5. Pull und Hashprüfung von PCK und PNG.

| Artefakt | Größe | SHA-256 |
|---|---:|---|
| [`game-studio-pr0-proof.pck`](evidence/game-studio-pr0-proof.pck) | 2,592 Bytes | `d744a72564ddf8afc29bb7f6eaa68b8884c984fbb13d68fbb8c7ddef0964f2f4` |
| [`game-studio-pr0-proof.png`](evidence/game-studio-pr0-proof.png) | 749 Bytes | `3c4cf29bbf1233c776f0e143bb878412e86c1db547ce06712ed4cb897e97269b` |

Der PNG-Frame ist `160×90`, RGBA und zeigt das tatsächlich gerenderte Testmotiv: dunkelblauer Hintergrund und hellblaues Smiley.

## 6. Nebenbefund: reale Incus-6-API

Der vorhandene Node-Agent verwendete `incus config show --format=json`; Incus 6.0.5 unterstützt dort kein JSON-Flag. Die Unit-Fakes hatten eine nicht existente CLI-Option modelliert. Der Adapter liest `expanded_devices` nun über:

```text
incus list <name> --format=json
```

Die Postcondition akzeptiert ausschließlich genau einen Eintrag mit exakt passendem Namen. Leere, fremde oder mehrdeutige Treffer scheitern fail-closed. Die Netzwerk-Tests decken diese Fälle ab.

## 7. Entscheidung

Das PR-0-Gate ist für die Incus/KVM-Isolations- und Teardown-Primitiven **bestanden**. PR 1 darf mit projektgebundener Core-Game-Ressource und administrativer Isolation-Freigabe beginnen. Produktive Game-Jobs bleiben bis zum Abschluss von PR 1–4 deaktiviert.
