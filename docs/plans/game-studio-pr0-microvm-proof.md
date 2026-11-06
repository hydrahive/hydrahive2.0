# Plan: Game Studio PR 0 — Godot-Linux-MicroVM-Nachweis

## Ziel

Vor jedem produktiven Game-Runner wird auf einer ausdrücklich freigegebenen separaten HydraHive-Testumgebung reproduzierbar bewiesen, dass ein kleines Godot-Projekt ausschließlich in einer frischen Incus-VM mit eigenem Kernel ausgeführt werden kann. Der Nachweis umfasst Isolation, Ressourcenlimits, vollständige Prozessbereinigung sowie echte Build-/Start-/Screenshot-Evidenz.

## Gewählter Weg

- **Incus-VM über den vorhandenen Node-Agent-Adapter `_incus_vm`**: gewählt, weil HydraHive diesen VM-Lifecycle bereits signiert und allowlistet.
- Kein direkter QEMU-Zweitpfad: würde Lifecycle, Ownership und Fehlersemantik duplizieren.
- Kein Firecracker-Pfad: für PR 0 wäre dies eine unnötige zusätzliche Jailer-/Kernel-Infrastruktur neben dem vorhandenen Incus/KVM-Weg.
- Kein Container- oder Host-Fallback: fehlender KVM-/Incus-Zugriff ist ein harter Fehler.

## Testziel

- ausdrücklich freigegebene separate Bare-Metal-Testumgebung
- Godot 4.4.1
- Incus-VM aus einem per Umgebungsvariable festgelegten Linux-Cloud-Image
- Standardlimits: 2 vCPU, 2048 MiB RAM, 10 GiB Root-Disk
- Gastnetzwerk `type=none`, keine Default-Route/DNS/Metadatenverbindung
- eigener Gastkernel und belegter VM-Typ; Container-/Mock-/Hostfallback sind unzulässig
- keine Hostgeräte, Hostpfade, Host-Sockets oder Host-Secrets im Gast; echte Cross-Project-Autorisierung folgt in PR 1/4
- positiv gelistetes Gast-Environment
- begrenzte Output-Fläche mit 64 MiB, 128 Inodes und maximaler Artefakt-/Dateianzahl
- Prozesslimit innerhalb des Gasts über eine systemd-Unit
- getrennte Cancel- und Timeout-Proben beenden jeweils die komplette VM und damit jeden Kindprozess
- Audit pinnt Incus/QEMU, Gastimage-Fingerprint, Gastkernel, Godot, Policy-Digest und Artefakthashes

## Dateien

- `node-agent/game_microvm_contract.py` — reine, nicht ausgelieferte Policy-/Konfigurationslogik.
- `node-agent/game_microvm_runtime.py` — nicht ausgelieferte Incus-/Gastsonden und fail-closed Capabilityprüfung.
- `node-agent/game_microvm_harness.py` — schlanker, nicht mit dem Wheel ausgelieferter Echtlauf-Orchestrator; VM-Namen und erlaubte Befehle werden intern erzeugt.
- `node-agent/tests/build_game_microvm_image.sh` — reproduzierbarer temporärer Xvfb-/Mesa-Imagebuilder; Builder hat Netzwerk, veröffentlichtes Proof-Image nicht.
- `node-agent/tests/test_game_runtime_microvm_smoke.py` — Standardtests plus opt-in Echtlauf mit `HH_GAME_MICROVM_TEST=1`.
- `node-agent/tests/fixtures/game_runtime_godot/project.godot` — minimales Godot-Projekt.
- `node-agent/tests/fixtures/game_runtime_godot/main.tscn` — sichtbare Testszene.
- `node-agent/tests/fixtures/game_runtime_godot/main.gd` — zeichnet das deterministische Motiv; Godots Movie Writer speichert den echten Viewport-Frame.
- `node-agent/tests/fixtures/game_runtime_godot/export_presets.cfg` — PCK-Export ohne externe Exporttemplates.
- `docs/audit/game-studio-linux-microvm-proof.md` — erst nach bestandenem Echtlauf; enthält Versionen, Befehle, Hashes und Ergebnisse.
- `docs/specs/game-studio-module-v0.1.md` — erst nach bestandenem Echtlauf um den Nachweisverweis ergänzen.

## Implementierungsreihenfolge

### Task 1: Fail-closed Harness-Vertrag

- [x] Unit-Test: Opt-in ohne `/dev/kvm`, Incus-Socket oder ausführbares Godot bricht mit stabilem Grund ab.
- [x] Unit-Test: VM-Name, Image und Ressourcenwerte werden begrenzt und nicht frei als zusätzliche Incus-Argumente übernommen.
- [x] RED nachweisen.
- [x] Minimalen Harness implementieren.
- [x] Tests GREEN.

### Task 2: Isolationsnachweis

- [x] Opt-in Test erzeugt die VM über `_incus_vm.execute` mit `network_mode=isolated`.
- [x] Expanded Config und Gastprobe bestätigen VM-Typ, eigenen Gastkernel, CPU/RAM/Disk und `eth0.type=none`.
- [x] Test lehnt Container-/Hostfallback und Hostgeräte (`gpu`, `usb`, `pci`, `proxy`, `unix-char`, `unix-block`, zusätzliche Host-Disk) ab.
- [x] Gast sieht nur Loopback, keine Default-Route/DNS/Metadatenverbindung und keine Docker-/Incus-Sockets.
- [x] Gast sieht weder Host-/Home-/Credential-Mounts noch den Host-Secret-Sentinel; echte Cross-Project-Guards werden erst mit Core-Projekten in PR 1/4 geprüft.
- [x] Gast-Environment entspricht einer festen Positivliste statt der Hostumgebung.

### Task 3: Godot-Evidenz

- [x] Godot-Binärdatei und Fixture werden nur in den Gast kopiert.
- [x] `--headless --editor --quit` validiert das Projekt im Gast.
- [x] `--export-pack` erzeugt ein PCK; SHA-256 und Größe werden erfasst.
- [x] Das exportierte PCK wird im Gast gestartet.
- [x] Die laufende Szene erzeugt eine echte Viewport-PNG; PNG-Signatur, Größe und SHA-256 werden geprüft.

### Task 4: Ressourcenlimits und Bereinigung

- [x] Gast-Output liegt auf einer begrenzten Fläche mit 64 MiB und 128 Inodes; Artefaktgröße und Dateianzahl werden dadurch hart begrenzt.
- [x] Gast-Unit läuft mit festem `TasksMax` und einem Kindprozess.
- [x] Cancel-Probe stoppt die VM über den vorhandenen Adapter und beendet den vollständigen Prozessbaum innerhalb der Frist.
- [x] Separate Timeout-Probe überschreitet bewusst die Laufzeitgrenze und erzwingt denselben vollständigen Teardown.
- [x] Nach Neustart sind Units und markierte Prozesse nicht vorhanden.
- [x] `finally` löscht die Test-VM auch bei Fehlern.

### Task 5: Echter Lauf und Audit

- [x] Ausschließlich die ausdrücklich freigegebene separate HydraHive-Testumgebung erhält temporäre Proof-Ressourcen.
- [x] Echtlauf mit explizitem Opt-in ausführen.
- [x] Auditbericht aus den strukturierten Ergebnissen erstellen; Skip/Mock gilt nie als positiver Nachweis, Versionen und Image-/Kernel-/Policy-Digests werden gepinnt.
- [x] Spec um den belegten Nachweis ergänzen.
- [x] Node-Agent-Gesamttests und `git diff --check` ausführen.

## Akzeptanzkriterien

- [x] Kein nicht vertrauenswürdiger Godot-/Projektprozess läuft auf dem Host; dort laufen ausschließlich Incus und Hypervisor.
- [x] Ohne Opt-in, echten Gastkernel und echte VM-Capability wird kein positiver Nachweis erzeugt; Skip/Mock/Container zählt nicht.
- [x] Externes Netzwerk, Default-Route/DNS/Metadaten, Hostgeräte, Hostmounts, Host-Sockets und Host-Secrets sind im Gast nicht verfügbar.
- [x] Environment ist positiv gelistet; CPU, RAM, Disk, Inodes, PIDs, Dateianzahl, Laufzeit und Outputgröße sind begrenzt.
- [x] Cancel und Timeout beseitigen VM und Kindprozesse jeweils innerhalb der dokumentierten Frist.
- [x] Validierung, Export, Start des Exports und Screenshot sind durch Hashes belegt; Versionen und Image-/Kernel-/Policy-Digests stehen im Audit.
- [x] Test-VM wird unabhängig vom Ergebnis entfernt.

## Nicht in PR 0

- kein produktiver `game-runtime/v1`-Provider;
- keine Core-API, Datenbankmigration oder Moduloberfläche;
- kein Unreal-Runner;
- keine automatische Installation von Incus, Godot oder Exporttemplates;
- keine dauerhafte Test-VM.
