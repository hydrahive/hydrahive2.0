# IDs in derselben Millisekunde in Reihenfolge (uuid7)

Task 4e5eaba5. Ein Test schlug manchmal ohne Grund fehl:
`test_compute_jobs.py::test_cancel_rejects_terminal_job_and_every_transition_is_audited`
(gemessen: 1 von 12 Läufen rot, Reihenfolge `job.cancelled` vor `job.queued`).

## Ursache

- `now_iso()` hat Millisekunden-Auflösung. Auftrag anlegen und abbrechen passieren oft in derselben Millisekunde,
  der Zeitstempel ist dann gleich.
- Die Abfrage sortiert nur nach `created_at` und hat keinen zweiten Schlüssel. Gleiche Zeitstempel kommen in
  beliebiger Reihenfolge.
- Der Code sortiert an mehreren Stellen zusätzlich nach der ID (`audit_id`, `job_id`, `id`). `uuid7()` setzt die
  12 Bit `rand_a` aber **zufällig**. Innerhalb derselben Millisekunde ist die Reihenfolge der IDs daher Zufall.
  Betroffen sind, nur selten:
  - `compute/audit.list_records`: Das Protokoll kann zwei Einträge derselben Millisekunde vertauscht zeigen.
  - `compute/_job_leases`: Bei zwei Aufträgen derselben Millisekunde kann der jüngere zuerst vergeben werden.
  - `projects/audit`, `runner/integrity_metrics`, `db/_mirror_embed`: dasselbe Muster.

## Lösung

1. **`uuid7()` monoton**, nach RFC 9562 §6.2 Methode 1: `rand_a` ist ein Zähler je Millisekunde.
   - Gleiche Millisekunde wie die letzte ID → Zähler + 1.
   - Läuft der Zähler über (4096 IDs in einer Millisekunde), wird der Zeitanteil um 1 ms weitergezählt.
   - Geht die Uhr zurück, bleibt der letzte Zeitanteil stehen. Neue IDs sind dann trotzdem größer.
   - Thread-sicher über eine Sperre. Gilt je Prozess, HydraHive läuft als ein Prozess.
   - `rand_b` bleibt zufällig (62 Bit), die IDs bleiben eindeutig und nicht erratbar wie heute. Format und Länge
     sind unverändert. Bestehende IDs bleiben gültig.
2. **Test**: Sortierung `ORDER BY created_at, rowid` (Einfügereihenfolge). Er hängt damit nicht mehr am
   Zeitstempel allein.

Nicht enthalten: Zeitstempel feiner machen (Format in vielen Tabellen, unnötig).

## Prüfung

- Rote Tests vorher:
  - 1.000 IDs bei angehaltener Uhr sind aufsteigend.
  - Eine zurückgehende Uhr ergibt trotzdem aufsteigende IDs.
  - Ein Zählerüberlauf ergibt aufsteigende IDs, und der Zeitanteil wird größer.
  - Format: Version 7, Variante 2.
  - `list_records` gibt bei gleichem Zeitstempel die neueste zuerst aus.
- Der Test zum Abbrechen läuft 50-mal grün.
- Volle Testreihe und Mutanten.
