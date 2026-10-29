# Update richtet incus nicht neu ein, wenn es schon läuft

**Stand:** 29.10.2026 · **Status:** Auftrag von Till („mach 1“) · **Task:** 004d8ee0
**Verwandt:** `installer/update.sh`, `installer/modules/70-containers.sh`, `container-nat-ports.md`

## Problem

`update.sh` entscheidet am **Namen** des Speichers, ob incus eingerichtet werden muss:

```
! incus storage list | grep -q "default"   →  70-containers.sh
```

`70-containers.sh` prüft dann `grep -q "default.*dir"` und ruft `incus admin init --preseed` auf. Das legt den
Speicher `default` (dir, Systemplatte) an und **überschreibt das Profil `default`** (Wurzel auf diesen Speicher).

Am 29.10. hatte der Hauptserver nach dem Umzug auf die SSD nur noch den Speicher `ssd`. Das Update um 13:50 hat
incus deshalb „neu eingerichtet“: Neue Container landeten wieder auf der Systemplatte. Bestehende Container
blieben heil, weil sie Wurzel und Netz selbst eingetragen haben.

## Entscheidung

1. **incus gilt als eingerichtet, sobald es mindestens einen Speicher gibt** – egal wie er heißt und welcher Treiber.
2. Neu eingerichtet wird **nur**, wenn es gar keinen Speicher gibt (frische Installation). Dann wie bisher:
   Speicher `default` (dir) und Profil `default` mit Wurzel darauf.
3. Ist incus eingerichtet, fasst das Skript **Speicher und Profil-Wurzel nicht an**.
4. Beide Prüfungen (`update.sh` und `70-containers.sh`) nutzen dieselben Funktionen aus
   `installer/lib/incus-init.sh`. So können sie nicht wieder auseinanderlaufen.
5. Antwortet incus nicht (Dienst aus), gilt das **nicht** als „leer“: Es wird nichts eingerichtet, nur ein Hinweis
   ins Log geschrieben. Lieber einmal nicht einrichten als einen laufenden incus überschreiben.

Unverändert: Das Profil `default` bekommt keine Netzwerkkarte. HydraHive trägt `eth0` beim Anlegen jedes
Containers selbst ein (`containers/incus_client.py`). Von Hand angelegte Container brauchen `-n br0`.

## Tests (`core/tests/test_incus_init_update.py`)

Ein nachgebautes `incus` im `PATH` schreibt jeden Aufruf mit.

- Nur Speicher `ssd` (btrfs): `ensure_incus_initialized` ruft **kein** `admin init` auf; `incus_is_initialized` ist wahr.
- Speicher `default` (dir): ebenso kein `admin init`.
- Kein Speicher: genau ein `admin init --preseed` mit Speicher `default`/dir und Profil-Wurzel darauf.
- incus antwortet nicht (Rückgabe ≠ 0): kein `admin init`, `incus_is_initialized` ist falsch, Hinweis im Log.
- `update.sh` fragt `incus_is_initialized` und nicht mehr nach dem Namen `default`.
- `70-containers.sh` ruft `ensure_incus_initialized` und enthält kein eigenes `admin init` mehr.
