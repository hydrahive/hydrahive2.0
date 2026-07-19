# Compute-Jobs

Jede Mutation an einem Remote-Workload (Container erstellen, starten, stoppen, löschen, inspizieren) läuft als **persistenter, signierter Job** auf einem Compute-Node. Jobs sind an Node und Generation gebunden und überstehen Verbindungsabbrüche, ohne nicht-idempotente Operationen blind zu wiederholen.

## Status

- **Eingereiht** – wartet auf Zuweisung an den Node.
- **Zugewiesen** – der Node hat den Job per Lease übernommen.
- **Läuft** – wird gerade ausgeführt.
- **Erfolgreich / Fehlgeschlagen** – terminaler Zustand mit Ergebnis bzw. Fehlercode.
- **Abgebrochen** – vom Nutzer beendet, sofern der Zustand das erlaubte.
- **Abgelaufen** – die Lease lief aus, ohne dass ein Ergebnis kam.

## Ereignis-Verlauf

Das Job-Detail zeigt eine lückenlose **Ereignis-Timeline** (Einreihung, Lease, Fortschritt, Ergebnis). Damit ist ein Jobfehler ohne Serverzugriff nachvollziehbar.

## Abbrechen

Ein Job kann nur in serverseitig erlaubten Zuständen abgebrochen werden. Bereits laufende, nicht idempotente Operationen werden **nicht** blind zurückgerollt.
