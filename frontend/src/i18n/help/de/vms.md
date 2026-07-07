# Virtuelle Maschinen (VMs)

## Was ist das?

Hier betreibst du **vollwertige virtuelle Computer** direkt auf dem HydraHive-
Server — echte Betriebssysteme (Linux, Windows …) in einer abgeschotteten
Umgebung. Technisch läuft das über **QEMU/KVM** (die native Virtualisierung von
Linux). Du siehst alle VMs als Kacheln, kannst sie starten/stoppen und dich per
**VNC-Konsole direkt im Browser** einloggen — wie ein Bildschirm, der an die VM
angeschlossen ist.

Denk an eine VM wie an einen **zweiten Rechner im Rechner**: eigene Festplatte,
eigenes Betriebssystem, eigenes Netzwerk — komplett getrennt vom Host.

## Wozu ist das gut?

- Ein **Testsystem** aufsetzen, ohne echte Hardware.
- Ein **anderes Betriebssystem** ausprobieren (z.B. Windows auf einem Linux-Server).
- Einen **Dienst isoliert** laufen lassen, der nicht das Hauptsystem berühren soll.
- Ein bestehendes Disk-Image (`qcow2`) importieren und weiterbetreiben.

## Kernbegriffe

- **ISO** — ein Installations-Abbild (z.B. der Windows- oder Ubuntu-Installer). Du
  lädst es einmal in die **ISO-Library** hoch und bootest neue VMs davon.
- **Disk / qcow2** — die virtuelle Festplatte der VM.
- **Snapshot** — ein eingefrorener Zustand der VM, zu dem du später zurückkehren
  kannst (praktisch vor riskanten Änderungen).
- **Bridged / Isoliert** — die Netzwerk-Betriebsart (siehe unten).
- **VNC-Konsole** — der Bildschirm der VM, im Browser bedienbar.

## Schritt-für-Schritt: erste VM erstellen

1. **Zuerst eine ISO hochladen**: Öffne die **ISO-Library** und lade das
   Installations-Abbild deines Betriebssystems hoch (der Tipp oben auf der Seite
   weist darauf hin).
2. **Neue VM** klicken.
3. **Name** vergeben (1–32 Zeichen, beginnt mit Buchstabe, nur `a-z A-Z 0-9 -`).
4. **Boot-Quelle** wählen:
   - **Aus ISO booten** — neue leere Disk + die ISO als Installations-Medium
     (der Normalfall für eine Neuinstallation).
   - **Importierte Disk** — eine vorhandene `qcow2` aus einem Disk-Import übernehmen.
   - **Leere Disk** — bootet ins Leere, bis du später ein System nachreichst.
5. **Netzwerk** wählen:
   - **Bridged (br0)** — die VM bekommt eine eigene IP aus deinem LAN (wie ein
     echtes Gerät im Netz).
   - **Isoliert** — kein Netzwerkzugang (maximal abgeschottet).
6. Optional **Disk-Interface / Machine-Type / Network-Device** anpassen
   (Standardwerte passen meist; `virtio` = schnellste Performance unter KVM,
   `sata` = kompatibler für ältere Gast-Systeme).
7. **VM erstellen**.
8. **Start** klicken → dann **Konsole**, um das Betriebssystem im Browser zu
   installieren/bedienen.

## Die Aktionen an jeder VM

- **Start** — VM hochfahren.
- **Konsole** — VNC-Bildschirm im Browser öffnen.
- **Stop** — sauberes Herunterfahren (ACPI-Shutdown, wie „Herunterfahren"-Knopf).
- **Aus** — hartes Ausschalten (SIGKILL, wie Stromstecker ziehen — nur wenn nötig).
- **Snapshots** — Zustände sichern/wiederherstellen.
- **QEMU-Log** — technisches Protokoll (hilft bei Startproblemen).
- **Bearbeiten / Löschen**.

## Typische Fehler

- **„Keine ISOs vorhanden"** — Erst ein Installations-Abbild in die ISO-Library
  hochladen, dann die VM erstellen.
- **VM startet nicht / bootet ins Leere** — Bei „Leere Disk" fehlt ein System;
  mit einer ISo booten oder eine importierte Disk verwenden. Das QEMU-Log gibt
  Hinweise.
- **Keine Netzwerkverbindung in der VM** — Netzwerk steht auf **Isoliert**; auf
  **Bridged** umstellen, wenn die VM ins Netz soll.
- **Konsole bleibt schwarz** — VM läuft evtl. noch nicht oder ist schon
  heruntergefahren; Status der Kachel prüfen.

## Tipps

- **Snapshot vor Risiko**: Vor Updates oder Experimenten einen Snapshot anlegen —
  Rückkehr ist ein Klick.
- **virtio bevorzugen**, wenn das Gast-OS es unterstützt (Linux immer, Windows mit
  Treiber) — deutlich schneller.
- **Sauber herunterfahren** (Stop/ACPI) statt „Aus", damit das Gast-Dateisystem
  keinen Schaden nimmt.
