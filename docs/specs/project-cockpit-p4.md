# Plan: Project-Cockpit P4 – Mounts und SMB

## Ziel

Projektgebundene SMB-Mounts sind direkt im Cockpit sichtbar und verwaltbar. Bestehende Mount-APIs, Validierung und Credential-Referenzen werden wiederverwendet.

## Umsetzung

- `MountsTab`, `AddMountForm`, `CreateMountForm` und `MountRow` einbetten.
- Explizit schließbares Overlay aus der Project-Cockpit-Topbar.
- Mounts können erstellt, dem Projekt zugewiesen und nach Bestätigung entfernt werden.
- Angezeigt werden UNC-Pfad, Read-only, Mountstatus und Fehlercode.

## Sicherheitsgrenzen

- Credential ist ausschließlich der Name einer vorhandenen Credential-Referenz, kein Passwortfeld.
- Keine Secrets oder aufgelösten Zugangsdaten anzeigen.
- Host, Share und Subpath werden weiterhin serverseitig validiert.

## Akzeptanzkriterien

- Zugeordnete Mounts und Zustände sind sichtbar.
- Vorhandene oder neue Mounts können zugewiesen werden.
- Entfernen verlangt Bestätigung.
- API- und Mountfehler bleiben sichtbar.
