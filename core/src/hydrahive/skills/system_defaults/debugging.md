---
name: debugging
description: Systematische Fehlersuche in vier Phasen – erst Ursache belegen, dann Muster vergleichen, eine Hypothese testen, mit rotem Test beheben. Nach drei gescheiterten Fixes die Architektur hinterfragen.
when_to_use: Wenn ein Bug gefunden werden soll oder etwas nicht funktioniert – Testfehler, Fehler im Betrieb, unerwartetes Verhalten, wacklige Tests, Build- oder Update-Fehler. Gerade unter Zeitdruck oder wenn ein schneller Fix naheliegt.
tools_required: [shell_exec, file_read]
---

# Systematische Fehlersuche

> Überarbeitet nach „systematic-debugging“ aus Superpowers v7.0.2 (github.com/obra/superpowers, MIT, © 2025 Jesse Vincent – Lizenztext: docs/third-party/superpowers-LICENSE), mit HydraHive-Erfahrungen.

## Die eiserne Regel

```
KEIN FIX OHNE BELEGTE URSACHE
```

Ohne abgeschlossene Phase 1 schlägst du keinen Fix vor. Das gilt besonders, wenn der Fehler einfach aussieht, wenn es eilt oder wenn schon ein Fix gescheitert ist. Eine Vermutung ist keine Diagnose – gibt es einen eigenen Faktencheck-Skill (z. B. `faktencheck-vor-diagnose`), lade ihn zusätzlich.

## Phase 1: Ursache untersuchen

1. **Fehlermeldung ganz lesen** – Stacktrace, Zeilennummern, Exit-Code, Warnungen. Oft steht die Lösung schon drin.
2. **Ist-Zustand erheben, nicht raten**
   - `journalctl -u <dienst> -n 50 --no-pager`, `systemctl status <dienst>`
   - `ss -tlnp | grep <port>`, `ps -ef | grep <prozess>`
   - CI: `gh run view <id> --log-failed` (bei Fehler „read-only file system“: `XDG_CACHE_HOME=<arbeitsordner>` setzen)
3. **Zuverlässig nachstellen** – genaue Schritte, kleinster Nachbau. Nicht nachstellbar → mehr Daten sammeln, nicht raten.
   Wackelt ein Test nur in der CI: die Lage dort nachbauen (parallele Worker, Daten früherer Tests in derselben DB, Ratenbremsen) und mit dem **Code von main** gegenprüfen, ob es am eigenen PR liegt.
4. **Letzte Änderungen prüfen** – `git log`, `git diff`, neue Abhängigkeiten, Konfiguration, Unterschiede zwischen Servern.
5. **Bei mehreren Komponenten: Belege an jeder Grenze sammeln** (Installer → Dienst → DB, API → Agent → Werkzeug). An jeder Grenze protokollieren, was hinein- und was herausgeht. Einmal laufen lassen, dann zeigt sich, **wo** es bricht.
   **Diagnose-Ausgaben verraten keine Geheimnisse:** nur „gesetzt/nicht gesetzt“ ausgeben, nie den Wert (`if [ -n "${VAR:-}" ]; then echo gesetzt; else echo fehlt; fi`; kein `env | grep`, kein `echo $TOKEN`).
6. **Datenfluss rückwärts verfolgen** – Wo entsteht der falsche Wert? Wer hat ihn übergeben? So weit zurück, bis du die Quelle hast. **An der Quelle beheben, nicht am Symptom.** Danach lohnt oft eine zweite Prüfung an einer weiteren Schicht (Verteidigung in der Tiefe).
7. **Ist es überhaupt das Ziel, das du denkst?** Prüfe Identität, bevor du Schlüsse ziehst: richtiger Server, richtiger Container, richtiger Commit, richtige DB (`hostname`, `boot_id`, `git rev-parse HEAD`, `/api/health`). Beispiel: Zwei Container mit gleicher MAC und IP – SSH landete zufällig auf dem falschen.

## Phase 2: Muster vergleichen

1. **Funktionierendes Gegenstück finden** – ähnlicher Code, der geht; ein Server, auf dem es läuft (Vergleich gegen funktionierenden Server, bevor du Code änderst).
2. **Referenz ganz lesen**, nicht überfliegen.
3. **Jeden Unterschied auflisten**, auch kleine. Nicht „das kann nicht wichtig sein“.
4. **Abhängigkeiten klären** – Einstellungen, Umgebung, Rechte (Dienstnutzer vs. root), Python-/bash-Version (Mac: bash 3.2).

## Phase 3: Hypothese testen

1. **Eine Hypothese, schriftlich**: „Ich denke, X ist die Ursache, weil Y.“
2. **Kleinste mögliche Änderung**, eine Variable auf einmal.
3. **Ergebnis prüfen** – bestätigt → Phase 4; nicht bestätigt → **neue** Hypothese, keine weiteren Fixes obendrauf.
4. **Weißt du es nicht, sag es**: „Ich verstehe X nicht.“ Nicht so tun als ob.

Hast du eine Diagnose schon gemeldet und sie stellt sich als falsch heraus: offen korrigieren, mit dem Beleg, der sie widerlegt – im Chat und im Task.

## Phase 4: Beheben

1. **Zuerst ein Test, der den Fehler zeigt und rot läuft** – automatisch, wenn möglich; sonst ein kleines Skript. Muss vor dem Fix existieren.
2. **Ein Fix für die belegte Ursache** – keine „wo ich schon dabei bin“-Verbesserungen, kein gebündeltes Refactoring.
3. **Prüfen** – Test grün, keine anderen Tests kaputt, ursprüngliches Symptom wirklich weg (siehe verification-before-completion). Gegenprobe: Fix zurücknehmen → Test rot.
4. **Hilft der Fix nicht:** anhalten und zählen. Unter drei Versuchen → zurück zu Phase 1 mit dem neuen Wissen.
5. **Drei oder mehr gescheiterte Fixes: Architektur hinterfragen.** Zeichen dafür: Jeder Fix legt an anderer Stelle ein neues Problem frei; Fixes bräuchten großen Umbau; jeder Fix erzeugt neue Symptome. Dann **keinen vierten Fix**, sondern mit Till besprechen, ob das Muster grundsätzlich trägt.

## Warnzeichen – zurück zu Phase 1

- „Schnell fixen, später untersuchen“
- „Ich ändere mal X und schaue“
- mehrere Änderungen auf einmal, dann testen
- „Test spare ich mir, ich prüfe von Hand“
- „Wahrscheinlich ist es X“
- Lösungen aufzählen, bevor der Datenfluss verfolgt ist
- „Noch ein Versuch“ nach zwei gescheiterten
- „Rerun, bis die CI grün ist“

**Signale vom Nutzer, dass du falsch liegst:** „Passiert das wirklich?“ (du hast nicht geprüft) – „Hör auf zu raten“ – „Schau nochmal nach“ – „Warum sollte das plötzlich nicht gehen?“. Dann anhalten und zu Phase 1.

## Ausreden und Wirklichkeit

| Ausrede | Wirklichkeit |
|---|---|
| „Ist einfach, kein Prozess nötig“ | Einfache Fehler haben auch Ursachen. Der Prozess ist dann schnell. |
| „Notfall, keine Zeit“ | Systematisch ist schneller als Raten und Zurückrollen. |
| „Test schreibe ich, wenn der Fix geht“ | Ungetestete Fixes halten nicht. Erst der rote Test beweist ihn. |
| „Mehrere Fixes auf einmal sparen Zeit“ | Dann weißt du nicht, was gewirkt hat. |
| „Ich sehe das Problem“ | Ein Symptom sehen ist nicht die Ursache verstehen. |
| „Der Test wackelt halt“ | Wackeln hat eine Ursache (fremde Daten, Zeit, Reihenfolge, Grenzen). Finden. |

## Wenn es wirklich keine Ursache im Code gibt

Zeigt die Untersuchung, dass es an Umgebung, Zeitverhalten oder etwas Externem liegt (Netz: „Connection reset by peer“ bei GitHub): Untersuchung festhalten, passend behandeln (Wiederholen, Zeitlimit, klare Meldung), Protokollierung für das nächste Mal. Aber: Die meisten „keine Ursache“-Fälle sind unvollständige Untersuchungen.

## Hilfstechniken

- **Warten auf Bedingungen statt fester Pausen:** nicht `sleep 30`, sondern in einer Schleife auf den Zustand prüfen, mit Obergrenze (`for i in $(seq 1 30); do <prüfen> && break; sleep 2; done`).
- **Verschmutzende Tests finden:** Hinterlässt ein Test Daten oder Dateien, die andere stören, Tests einzeln mit der Prüfung danach laufen lassen und halbieren, bis der Verursacher feststeht. Gegenmittel: nur eigene Zeilen aufräumen (`tests/_own_rows.py`), Budgets aus den tatsächlich vorhandenen Daten ableiten.
- **Bisektion:** `git bisect` zwischen letztem guten und erstem schlechten Commit.
