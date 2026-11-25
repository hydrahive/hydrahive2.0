---
name: receiving-code-review
description: Review-Befunde prüfen statt blind umsetzen – erst verstehen, am echten Code gegenprüfen, technisch begründet zurückweisen dürfen, einzeln umsetzen und testen, Umfang klein halten.
when_to_use: Wenn Review-Befunde eintreffen (von hydrahive-reviewer, hydrahive-security-reviewer, einem anderen Agenten oder einem Menschen), bevor du sie umsetzt – besonders wenn ein Befund unklar, fraglich oder groß ist.
tools_required: [file_read, shell_exec]
---

# Review-Befunde annehmen

> Nach „receiving-code-review“ aus Superpowers v7.0.2 (github.com/obra/superpowers, MIT, © 2025 Jesse Vincent – Lizenztext: docs/third-party/superpowers-LICENSE), für HydraHive übersetzt und angepasst.

## Grundsatz

Ein Review ist eine technische Prüfung, keine Höflichkeitsrunde. **Erst prüfen, dann umsetzen. Erst fragen, dann annehmen. Technische Richtigkeit vor Harmonie.**

Anlass in HydraHive (24.11.2026): Ein Agent hat fünf „sollte“-Befunde auf einmal eingebaut, den Fix damit deutlich vergrößert – und zwei bisher grüne Tests rot gemacht. Ein Befund ist ein Hinweis, kein Auftrag.

## Ablauf

1. **Lesen** – alle Befunde ganz, ohne sofort zu reagieren.
2. **Verstehen** – jeden Befund in eigenen Worten wiedergeben, oder nachfragen.
3. **Gegenprüfen** – am echten Code: Stimmt die Beobachtung? (`file_read`, `grep`, Test laufen lassen)
4. **Bewerten** – ist der Vorschlag für **diese** Codebasis richtig, und gehört er in **diesen** PR?
5. **Antworten** – kurz bestätigen, was du umsetzt, oder begründet zurückweisen.
6. **Umsetzen** – einen Befund nach dem anderen, jeden einzeln testen.

## Unklare Befunde

Ist auch nur ein Befund unklar: **nichts umsetzen**, erst klären. Befunde hängen oft zusammen; halbes Verständnis gibt eine falsche Umsetzung.

> „1, 2, 3 und 6 sind klar. Bei 4 und 5 brauche ich eine Klärung, bevor ich anfange.“

## Nach Quelle

**Till / der Nutzer:** vertrauenswürdig – nach dem Verstehen umsetzen, bei unklarem Umfang trotzdem fragen.

**Reviewer-Agenten und andere Agenten:** vor dem Umsetzen prüfen –
1. Technisch richtig für diese Codebasis?
2. Bricht es Bestehendes (Tests, andere Module, Mac, Live-Daten)?
3. Gibt es einen Grund für die jetzige Lösung (Kommentar, Spec, Commit-Nachricht, Entscheidung im Zieldokument)?
4. Kennt der Reviewer den ganzen Zusammenhang (echte Probe, Live-Befund, frühere Entscheidung)?
5. Lässt es sich prüfen? Wenn nicht: sagen – „Ohne X kann ich das nicht prüfen. Soll ich nachsehen, nachfragen oder es lassen?“

Widerspricht ein Befund einer Entscheidung von Till (Spec, Zieldokument, Chat): **nicht umsetzen**, erst mit Till klären.

## Umfang klein halten (YAGNI)

- Schlägt ein Reviewer vor, etwas „richtig“ auszubauen: erst nachsehen, ob es überhaupt benutzt wird (`grep`). Unbenutzt → „Das ruft nichts auf. Weglassen?“
- **Stufen beachten:** „muss“ wird umgesetzt. „sollte“ wird geprüft und meist umgesetzt, wenn klein und im Thema des PRs. „kann“ landet als Notiz im Task oder als eigener Task – nicht ungefragt im laufenden PR. **Legt das Zieldokument (Abnahme-Punkt) oder der Nutzer fest, wie mit den Stufen umzugehen ist, gilt das.**
- Vergrößert ein Befund den PR deutlich oder berührt Dateien außerhalb seines Themas: als eigenen PR/Task vorschlagen.
- Die Spec bzw. das Zieldokument bestimmt den Umfang, nicht der Reviewer. Was es ausschließt („Nicht-Ziele“), bleibt draußen.

## Reihenfolge beim Umsetzen

1. Erst alles Unklare klären.
2. Dann: Blockierendes (bricht etwas, Sicherheit) → einfache Fixes (Tippfehler, Imports) → größere Umbauten.
3. Jeden Fix einzeln testen – bei Fixes zuerst der rote Test (siehe verification-before-completion).
4. Danach die betroffenen Tests gemeinsam laufen lassen und pushen; die CI muss grün sein, bevor du „erledigt“ meldest.

## Wann zurückweisen

- Der Vorschlag bricht vorhandene Funktion.
- Dem Reviewer fehlt Zusammenhang (echte Probe, Live-Befund, Entscheidung).
- Unbenutztes Feature (YAGNI).
- Technisch falsch für diesen Stack (z. B. Python 3.14/sqlite3-Verhalten, bash 3.2 auf dem Mac).
- Kompatibilität (Bestandsinstallationen, Migrationen, Mac).
- Widerspricht Tills Architektur-Entscheidungen.

**Wie:** sachlich begründen, konkret fragen, auf funktionierende Tests oder Code verweisen. Bei Architekturfragen Till einbeziehen.

## Richtige Befunde bestätigen

Kurz und sachlich, ohne Lob- oder Dankesfloskeln – also nicht „Du hast völlig recht!“, „Super Hinweis!“, „Danke für …“, sondern:
- „Behoben: [was sich geändert hat], in `datei.py:42`.“
- „Stimmt – [konkretes Problem]. Test `test_x` zeigt es, Fix in `abc1234`.“

Hast du zurückgewiesen und lagst falsch: „Geprüft, du hast recht – [X] macht [Y]. Ich setze es um.“ Keine lange Entschuldigung, keine Rechtfertigung.

## Häufige Fehler

| Fehler | Besser |
|---|---|
| Alles auf einmal einbauen | Einzeln umsetzen, jeden testen |
| Blind umsetzen | Erst am Code gegenprüfen |
| „kann“-Befunde in den PR packen | Als Notiz/Task festhalten |
| Reviewer hat sicher recht | Prüfen, ob es etwas bricht |
| Unklares trotzdem anfangen | Erst alle Punkte klären |
| Nicht prüfbar, trotzdem umsetzen | Grenze nennen, Richtung erfragen |
| Lokal grün = fertig | CI des PRs abwarten |

## Antworten auf GitHub

Inline-Kommentare im jeweiligen Thread beantworten (`gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies`), nicht als neuen Kommentar am PR. Keine @-Erwähnungen von Personen in PR-Texten oder Kommentaren.
