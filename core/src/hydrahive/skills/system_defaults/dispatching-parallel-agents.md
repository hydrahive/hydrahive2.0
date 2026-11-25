---
name: dispatching-parallel-agents
description: Aufträge an Agenten zuschneiden und parallel vergeben – ein Agent je unabhängigem Teilproblem, eigenständiger Zusammenhang statt Gesprächsverlauf, klares Ziel, Grenzen und Rückgabe, in 20 Minuten machbar; Ergebnisse selbst gegenprüfen.
when_to_use: Wenn eine Aufgabe zwei oder mehr unabhängige Teilprobleme hat, bei paralleler Analyse (Review + Security, mehrere Testdateien mit verschiedenen Ursachen), und vor jedem ask_agent-Auftrag an einen Projekt-Agenten oder Spezialisten.
tools_required: [ask_agent]
---

# Aufträge an Agenten vergeben

> Überarbeitet nach „dispatching-parallel-agents“ (und Lehren aus „subagent-driven-development“) in Superpowers v7.0.2 (github.com/obra/superpowers, MIT, © 2025 Jesse Vincent – Lizenztext: docs/third-party/superpowers-LICENSE).

## Grundsatz

Ein Agent bekommt **genau den Zusammenhang, den er braucht – nie deinen Gesprächsverlauf.** Du baust ihn bewusst zusammen. Das hält ihn auf Kurs und deinen eigenen Zusammenhang frei für die Koordination.

**Ein Agent je unabhängigem Teilproblem.** Mehrere unabhängige Aufträge im selben Zug vergeben – sie laufen gleichzeitig.

## Wann parallel

**Ja, wenn:**
- Teilprobleme unabhängig sind (kein geteilter Zustand, keine gemeinsamen Dateien)
- verschiedene Blickwinkel gefragt sind (hydrahive-reviewer + hydrahive-security-reviewer, beide nur lesend)
- mehrere Testdateien aus verschiedenen Gründen rot sind
- jedes Problem ohne die anderen verständlich ist

**Nein, wenn:**
- die Fehler zusammenhängen (einer behoben, vielleicht alle weg) – erst gemeinsam untersuchen
- Aufgabe B das Ergebnis von A braucht
- beide dieselbe Datei oder denselben Branch schreiben würden
- noch unklar ist, was überhaupt kaputt ist (erst selbst eingrenzen, siehe `debugging`)

## Aufbau eines Auftrags (`ask_agent`)

- **goal** – ein Satz, prüfbar: was am Ende erreicht ist.
- **task** – was genau zu tun ist; Arbeitsort (Worktree unter `_work/wt/…`, Branch, PR-Nummer); was **nicht** zu tun ist („nicht mergen“, „nur lesen, keine Commits“, „nur Tests ändern“).
- **known** – was du schon weißt: Befunde mit Datei:Zeile, Fehlermeldungen wörtlich, Messwerte, was ausgeschlossen ist, frühere Läufe. Spart dem Agenten das Neusuchen – und damit Zeit bis zum Timeout.
- **deliverable** – was zurückkommen soll: PR-Nummer, Commits, CI-Status, Befundliste mit Datei:Zeile und Stufe.
- **ziel_doc + abnahme** – bei feature/bug_fix/refactor Pflicht; Abnahme-IDs im Format Buchstaben+Ziffern (`P3`, `UT1`).
- **task_type** – `review` für reine Prüfungen.

Gute Aufträge sind **fokussiert** (ein Problem), **eigenständig** (aller nötige Zusammenhang drin) und **genau in der Rückgabe**.

## Zuschnitt auf die Laufzeit

Ein Projekt-Agent bricht nach 20 Minuten ab. Deshalb:
- **Klein schneiden:** ein Auftrag = was in deutlich unter 20 Minuten fertig wird. Lieber zwei Aufträge nacheinander (erst Tests und Fixes, dann Reviews) als einer, der im Timeout endet.
- **Früh sichern:** Draft-PR nach wenigen Minuten, nach jedem Teilstück committen und pushen – dann geht bei einem Abbruch nichts verloren.
- **Nichts neu messen oder suchen lassen**, was schon bekannt ist – Werte in `known` mitgeben.
- **Reviews nur lesend** beauftragen, wenn du selbst einarbeitest. Ein Review-Agent, der Befunde gleich umsetzt, vergrößert den PR und kann die CI rot machen.
- Agenten starten **keine weiteren Agenten** für eine zweite Meinung – das verdoppelt Kosten und Zeit.
- **Kleine gleichartige Aufgaben bündeln** statt viele Einzelaufträge.
- **Unklarheiten im Auftrag entscheidet der Agent selbst und hält die Entscheidung fest**, statt stehen zu bleiben – nur Zerstörerisches oder Unumkehrbares wartet auf den Nutzer. Sag das im Auftrag, wenn es passt.
- Ist eine Kleinigkeit schneller selbst erledigt als beauftragt: selbst machen.

## Häufige Fehler

| Schlecht | Besser |
|---|---|
| „Bring alle Tests in Ordnung“ | „Repariere die 3 roten Tests in `test_x.py`: …“ |
| „Behebe die Race Condition“ | Fehlermeldungen und Testnamen wörtlich mitgeben |
| keine Grenzen – Agent baut alles um | „Produktivcode nicht ändern“ / „nur diese Datei“ |
| „Mach das fertig“ | „Zurück: Ursache, Änderungen, PR, CI-Status“ |
| Review + Umsetzen in einem Auftrag | Review nur lesend, Umsetzen getrennt |
| Zeitlimit erhöhen statt Ursache | „Nicht einfach Timeouts erhöhen – finde die Ursache“ |

## Nach der Rückkehr

1. Jeden Bericht lesen – er ist eine **Behauptung, kein Beweis** (siehe `verification-before-completion`).
2. Selbst gegenprüfen: Commits und Diff da? CI auf dem **aktuellen** Head grün? Bei Timeout: was ist gepusht, was liegt nur lokal?
3. Prüfen, dass parallele Änderungen sich nicht widersprechen; betroffene Tests gemeinsam laufen lassen.
4. Befunde aus Reviews nach `receiving-code-review` behandeln: Duplikate zusammenführen, nach Schwere sortieren, „muss“ zuerst.
5. Dem Nutzer knapp berichten – mit dem, was du selbst geprüft hast, und dem, was offen ist.
