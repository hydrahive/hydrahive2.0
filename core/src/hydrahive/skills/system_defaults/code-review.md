---
name: code-review
description: Code-Review durchführen oder anfordern – gegen Spec und Plan prüfen, Ungenanntes nach der Erwartung eines vernünftigen Nutzers bewerten, Liste „nicht beurteilt“, Stufen muss/sollte/kann mit Datei:Zeile, klares Urteil, jeder wichtige Fund wird ein Test.
when_to_use: Wenn der Nutzer um ein Code-Review oder eine Bug-Suche bittet, wenn du als Reviewer beauftragt bist, oder bevor du selbst ein Review anforderst (nach einer Aufgabe, vor dem Merge).
tools_required: [file_read, shell_exec]
---

# Code-Review

> Ergänzt um Teile aus „requesting-code-review“ in Superpowers v7.0.2 (github.com/obra/superpowers, MIT, © 2025 Jesse Vincent – Lizenztext: docs/third-party/superpowers-LICENSE).

## Review anfordern

Früh und oft: nach jeder Aufgabe, nach einem größeren Stück, **immer vor dem Merge**. Der Reviewer bekommt genau zugeschnittenen Zusammenhang – nie deinen Gesprächsverlauf:
- was gebaut wurde (ein, zwei Sätze),
- was es tun soll: Spec, Plan oder Zieldokument mit Pfad,
- den Bereich: PR-Nummer oder `BASE..HEAD` (`git merge-base origin/main HEAD`),
- bei Bedarf: worauf besonders achten (Root-Rechte, Migration, Mac).

In HydraHive: `hydrahive-reviewer`; bei Auth, Root, Verteilung, Volltext oder Schreibzugriffen zusätzlich `hydrahive-security-reviewer`. Für ein reines Review: **nur lesen** (`gh pr diff`, `git show`), keine Commits.

**Als Auftraggeber verboten:** dem Reviewer vorab sagen, was er übersehen oder als „höchstens Kleinigkeit“ einstufen soll. Ein Fehler, den der Plan selbst vorschreibt, wird gemeldet und der Nutzer entscheidet – nicht durchgewunken. Mit den Befunden umgehen: Skill `receiving-code-review`.

## Review durchführen

Prüfe in dieser Reihenfolge:

1. **Passt es zum Plan / zur Spec?** Ist alles Geplante da? Sind Abweichungen begründete Verbesserungen oder Fehler? Liegt ein Problem im Plan selbst, das sagen.
2. **Korrektheit** – tut der Code, was er soll? Off-by-One, Randfälle, Race Conditions, None/leer, Fehlerpfade, Rückweg.
3. **Sicherheit** – Eingabeprüfung, Injection (SQL, Shell, Pfad), Auth-Prüfung, Geheimnisse in Logs/Antworten, root-Schreibzugriffe in Nutzer-Verzeichnisse, Symlinks.
4. **Fehlerbehandlung** – werden Fehler geschluckt? Klare Meldungen mit Kontext?
5. **Klarheit und Konsistenz** – Namen, Schichten, Stil der Codebasis, HydraHive-Regeln (`hh-review`: Dateigröße, keine `print()`, Settings-Singleton).
6. **Tests** – prüfen sie echtes Verhalten (nicht nur Mocks oder Textsuche)? Randfälle? Wären sie ohne den Fix rot?
7. **Betrieb** – Migration und Bestandsdaten, Abwärtskompatibilität, Mac, i18n (de/en).
8. **Performance** – N+1, unnötige Schleifen, große Kopien – nur wenn relevant.

**Die Spec ist eine Vision, keine vollständige Liste.** Sie sagt, was die Software können muss, nicht jede Eingabe und Lage, der sie begegnet. Wozu sie schweigt, bewertest du nach dem, **was ein vernünftiger Mensch erwarten würde**, der die Software benutzt: Seine Erwartung ist eine Anforderung, das Schweigen der Spec keine Erlaubnis. Stufe solche Befunde nach ihrer Wirkung auf diesen Menschen ein – ein Absturz bei einer ungenannten, aber naheliegenden Eingabe ist keine Kleinigkeit.

Was du **nicht** machst:
- „sieht gut aus“, ohne gelesen zu haben; Kommentare zu Code, den du nicht gelesen hast
- Kleinkram als „muss“ einstufen; Geschmacksfragen ohne Wirkung
- Umbauten vorschlagen, die den Umfang sprengen – als eigenen Task empfehlen
- weitere Agenten für eine zweite Meinung starten – du machst das Review selbst; ist es groß, in mehreren Durchgängen und das sagen
- am Arbeitsstand etwas ändern (kein Checkout, kein Commit); eine andere Fassung nur in einem eigenen Worktree ansehen

## Antwort-Format

**Stärken** – was gut gemacht ist, konkret (genaues Lob hilft, dem Rest zu vertrauen).

**Befunde** nach tatsächlicher Schwere, je Befund: `Datei:Zeile`, was falsch ist, warum es zählt, wie beheben (wenn nicht offensichtlich):
- **muss** – Fehler, Sicherheit, Datenverlust, kaputte Funktion
- **sollte** – Architektur, fehlende Teile, schwache Fehlerbehandlung, Testlücken
- **kann** – Stil, Optimierung, Doku

**Nicht beurteilt** – vor dem Urteil: jedes Verhalten, das du erwogen und als außerhalb von Plan/Spec beiseitegelegt hast, je eine Zeile mit Grund. Der Auftraggeber entscheidet jede Zeile; nichts verschwindet still. Leere Liste heißt: nichts beiseitegelegt.

**Urteil:** mergebar? **Ja / Nein / Mit Fixes** – mit ein, zwei Sätzen technischer Begründung.

## Jeder Fund wird ein Test

Für jeden „muss“- und jeden „sollte“-Fund nennst du den **Test, der ihn festhält**: Was wird geprüft, und warum ist der Test ohne den Fix rot? So kommt dieselbe Fehlerart nicht unbemerkt wieder. Lässt sich ein Fund nicht automatisch prüfen (z. B. nur auf echter Hardware), sag das ausdrücklich und nenne den Grund. Er gehört dann als „Kein Test: <Begründung>“ in die PR-Beschreibung (Regel: docs/specs/fix-test-guard.md).
