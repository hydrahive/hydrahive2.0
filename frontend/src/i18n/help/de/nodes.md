# Compute-Nodes

Compute-Nodes sind freigegebene Ubuntu-Hosts, auf denen HydraHive über einen **ausgehend verbundenen Agent** Container (und später VMs) betreibt. Der lokale Host ist immer als Node `local` vorhanden und braucht kein Enrollment.

## Node koppeln

1. **Node koppeln** öffnen und einen eindeutigen Namen vergeben.
2. Den einmaligen **Enrollment-Token** kopieren — er wird nur einmal angezeigt.
3. Auf dem Zielhost `hydrahive-node enroll` mit dem Token ausführen.
4. Der Node erscheint danach als **Wartet** in der Liste.

## Freigeben

Ein wartender Node zeigt einen **Zertifikat-Fingerprint**. Vergleiche ihn mit der Ausgabe des Agents und gib den Node nur bei exakter Übereinstimmung frei. Erst danach nimmt der Node Workloads an.

## Status

- **Online** – verbunden und einsatzbereit.
- **Eingeschränkt** – verbunden, aber mit Health-Warnungen.
- **Offline** – kein aktueller Heartbeat.
- **Wird geleert** – nimmt keine neuen Aktivierungsjobs mehr an; Stop/Delete/Inspect bleiben möglich.
- **Deaktiviert** – manuell pausiert.
- **Widerrufen** – Identität dauerhaft ungültig.

## Aktionen

**Leeren** stoppt neue Platzierungen sanft. **Deaktivieren** pausiert den Node. **Widerrufen** macht die Node-Identität dauerhaft ungültig — das lässt sich nicht rückgängig machen.
