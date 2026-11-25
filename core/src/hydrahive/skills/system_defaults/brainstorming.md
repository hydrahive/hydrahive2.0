---
name: brainstorming
description: Erst verstehen, dann bauen – selbst nachlesen statt fragen, zuerst das Warum klären, nur Fragen stellen, deren Antwort etwas ändert, Ansätze mit Empfehlung vorlegen, Aufwand passend zur Aufgabe, Design freigeben lassen, dann Plan.
when_to_use: Vor jeder neuen Funktion oder Änderung mit offenen Punkten, bei Architektur-Entscheidungen, wenn der Nutzer eine Idee schildert oder „lass uns überlegen“ sagt, wenn du „ich fang einfach an“ denkst, ohne zu wissen, was er wirklich will.
tools_required: [file_read, file_write, shell_exec]
---

# Brainstorming – erst verstehen, dann bauen

> Nach „brainstorming“ aus Superpowers v7.0.2 (github.com/obra/superpowers, MIT, © 2025 Jesse Vincent – Lizenztext: docs/third-party/superpowers-LICENSE), für HydraHive übersetzt und angepasst.

## Zuerst: Was weißt du wirklich?

Bevor du antwortest: Was weißt du darüber, **was** der Nutzer will und **warum**?

- **Alles Wichtige steht in der Anfrage** („mach das Icon kornblumenblau“): Das ist eine kleine, klare Aufgabe. Erledigen und sagen, was du getan hast.
- **Etwas Wesentliches fehlt:** das Gespräch beginnen.

Bevor du baust, in dieser Reihenfolge:
1. Die Ansätze in einer eigenen Nachricht vorlegen, der Nutzer wählt einen.
2. Das Design aufschreiben – kurz oder ausführlich (siehe „Aufwand einschätzen“).
3. Freigabe dieses Designs holen.
4. Danach den Skill `writing-plans` laden.

Ist beim Schreiben der ersten Nachricht nichts offen und gibt es nur einen sinnvollen Weg, passieren 1–3 schon in dieser Nachricht.

Kein „Bauen“ sind: ein vereinbarter Wegwerf-Versuch (Spike) und das Erledigen der Aufgabe, nachdem der Nutzer auf die Fragen verzichtet hat.

## Erst nachsehen, dann fragen

In einem bestehenden Projekt, oder wenn der Nutzer Zusammenhang mitgibt (Spec, Zieldokument, Task, Idee, Board, Dateien, früheres Gespräch): **vor der ersten Nachricht lesen.** Das Genannte und den Code, an dem es hängt – so lange, bis du erklären kannst, wie die betroffenen Teile heute arbeiten und was die Änderung berührt. Nutze dafür Bereichs-Skills (`bereich-…`), `code-graph` und – falls die Module installiert sind – `task_read`, `idea_read`, `blueprint_read`.

**Nie fragen, was das Projekt oder der Zusammenhang schon beantwortet, und nie wieder aufmachen, was schon entschieden ist.**

## Deine erste Nachricht

Bring die Sache voran, auf eine dieser Arten:

- **Der Nutzer hat schon gesagt, was er will** (Spec, Zieldokument, ausführliche Anfrage): rund 200 Wörter für die ganze Nachricht.
  - Die Anfrage in eigenen Worten zurückgeben, damit er sieht, ob du die Form hast: was, für wen, warum – soweit gesagt.
  - Ergänzen, was du gefunden hast: wie es heute läuft, was die Änderung berührt. Hast du etwas gefunden, das er vielleicht nicht bedacht hat und das die Anfrage oder den Bau ändert (eine Grenze, ein Widerspruch, ein günstigerer Weg): klar sagen.
  - Eine Zeile, die zur Korrektur einlädt.
  - **Hat er nicht gesagt, warum er es will** – auch wenn du es ahnst –: danach fragen. Eine offene Frage in seinen Worten, ohne Auswahl.
  - Weißt du das Warum, und ist etwas offen, dessen Antwort ändert, was gebaut wird: nach dem fragen, das am meisten ändert. Lassen sich die Möglichkeiten benennen, jede kurz skizzieren, mit dem, was sie kostet, und welche du nehmen würdest.
  - Ist nichts offen und es gibt einen sinnvollen Weg: mit dem kurzen Design enden (Ansatz, eine Zeile, warum die anderen nicht passen, Design in wenigen Zeilen) und um Freigabe bitten. Seine Freigabe gilt für Ansatz und Design.
  - Specs sind oft unvollständig – bestätigen lassen, bevor du darauf baust.
- **Er hat es nicht gesagt:** eine offene Frage in seinen Worten zum größten offenen Punkt, und warum du fragst (was die Antwort ändern würde). Beispiel für „eine Seite für meine Bäckerei“: „Geht es vor allem um Leute, die überlegen vorbeizukommen, würde ich mit Öffnungszeiten und der heutigen Auslage anfangen – Bestellungen wären eine andere Seite. Was soll jemand tun, der auf der Seite landet?“

Wie die Nachricht endet:
- **Er hat ausdrücklich um Brainstorming/Überlegen gebeten:** dort enden.
- **Hat er nicht:** eine leichte Zeile anbieten, direkt loszulegen („Oder soll ich einfach anfangen?“). Nimmt er an, ist dieser Skill fertig: wichtige Bau-Entscheidungen (Sprache, Modul oder Kern, Bibliothek) in einer Zeile nennen und die Aufgabe normal erledigen.

## Das Gespräch

**Frag nur, wenn die Antwort ändert, was gebaut wird, und weder Anfrage noch Projekt sie liefern.** Sonst deine Entscheidung mit Grund als Vorschlag nennen, den er korrigieren kann, und weitermachen. Ablauf-Fragen sind immer deine Entscheidung (aufschreiben, wo Dateien hinkommen, weiter nachsehen, wie du etwas zeigst) – erledigen und sagen.

- Eine Frage auf einmal. Klare Sprache, eher etwas über seinem Fachwortschatz als darunter; seine Begriffe verwenden, keinen Prozess-Jargon, diesen Skill nicht zitieren.
- Klar und knapp, das Wichtigste zuerst. Bei Befunden die wichtigsten nennen, den Rest anbieten.
- **Erst beschreiben lassen.** Solange du das Warum nicht kennst: offene Fragen ohne Beispielantworten – seine eigenen Worte tragen Absicht, die deine Optionen nicht haben. Kennst du das Warum und es gibt benennbare Möglichkeiten: jede konkret skizzieren, mit Abwägung und deiner Wahl. Sagt er „rat einfach“ oder „was meinst du?“: etwas Konkretes vorschlagen.
- **Wie es gebaut wird.** Lies aus seiner Art zu reden, welche Bau-Entscheidungen er selbst treffen will. Wer nach dem Wie oder nach Abwägungen fragt, will Optionen mit Empfehlung. Wer über Ergebnisse redet, überlässt dir das Wie: entscheiden und je eine Zeile nennen. Auf vorhandenem Aufbau aufsetzen (Modul vs. Kern, vorhandene Muster). Deine Entscheidungen stehen im Design als deine, nie als „vereinbart“.
- **Gebiet, kein Fragebogen** – nie vorlesen: was es ist und was es besonders macht; warum jetzt und woran man Erfolg sieht; Ziele, Nicht-Ziele, Anti-Ziele (was es zum Fehlschlag machte, obwohl es technisch läuft); Vorbilder (gesehen, gemocht, gehasst); was es heute gibt und was schon versucht wurde; die Details, die ihm wichtig sind.
- **Jede Frage konkret** zu seinem Vorhaben, aufbauend auf seiner letzten Antwort oder einem Fund – so, dass sie ihm eine Folge oder einen Fall zeigt, den er übersehen haben könnte („Die Abstimmung schließt vor dem Treffen, und zwei sind diesen Monat neu dazugekommen. Darf, wer mitten in der Runde kommt, mit abstimmen?“).
- **Nachsehen.** Hilft es, tiefer zu schauen (Code, seine Daten, Web, Datamining zu früheren Gesprächen): tun und sagen, was du gesucht und gefunden hast.
- **Zeigen statt beschreiben.** Hilft Sehen mehr als Lesen: eine kurze Text-Skizze. Für Abläufe, Aufbau und Varianten – falls installiert – Skill `diagramme` oder ein Blueprint-Board (`blueprint_propose`).
- **Wegwerf-Versuch.** Ein schneller Spike ist oft der billigste Weg herauszufinden, was er will oder ob etwas geht. Anbieten, wenn es hilft. Spikes haben keine oder minimale Tests und überspringen Plan und Review. Was er gezeigt hat, zurück ins Gespräch bringen.

### Ansätze vorlegen

Hast du verstanden, was er will, und bevor du etwas aufschreibst: die Bauwege **in einer eigenen Nachricht**. Mehrere echte Alternativen überlegen, die schwachen streichen (auch die, die gegen sein Warum arbeiten oder die der Bestand ausschließt). Die zwei oder drei übrigen so konkret skizzieren, dass man sie sich vorstellen kann – mit dem, was jede kostet. **Eine empfehlen und sagen, warum**, dann fragen, welchen Weg er will. Hat er dir das Wie überlassen: sagen, dass du deine Wahl nimmst. Gibt es wirklich nur einen sinnvollen Weg: das sagen und erklären, warum die anderen nicht passen.

## Zurückspiegeln

Sobald du einen Teil gut genug verstehst, um ihn zu beschreiben (wofür, für wen, wie sich ein Stück verhält): ihn in rund 200–300 Wörtern zurückgeben, dann zur nächsten Frage. Zurückspiegeln und Fragen wechseln sich ab.

**Nur was er gesagt hat, steht als seins da.** Was du ergänzt hast, steht als dein Vorschlag mit Grund. Jeden Teil mit der Frage beenden, was falsch ist oder fehlt.

## Aufwand einschätzen

Ist klar, was er will, und hat er einen Ansatz gewählt: in klaren Worten sagen, wie groß es ist. Er kann widersprechen.

| Größe | Design |
|---|---|
| Kleine Änderung | kurz: was ihr schon besprochen habt, aufgeschrieben (im Chat oder als Task-Notiz) |
| Projekt | ausführliches schriftliches Design (unten) |

Kurz oder lang – das Design hat einen Teil **Ansätze**: die zwei, drei erwogenen Wege, was jeder kostet, welchen er gewählt hat und warum.

Wächst es unterwegs: anhalten, sagen, eine Größe hochgehen. Sind es eigentlich mehrere unabhängige Vorhaben: sagen, Reihenfolge vereinbaren, einzeln durchgehen.

## Das schriftliche Design

Ein schlichtes Dokument, nach dem eine fähige Entwicklerin planen kann, ohne beim Nutzer nachzufragen:
- Absicht und das Warum
- Ziele, Nicht-Ziele, Anti-Ziele
- Grenzen und Vorgaben
- Ansätze (siehe oben)
- die Teile des Wie, die er entschieden hat – so, wie er sie entschieden hat
- was der Umsetzung überlassen bleibt
- bei Aufträgen an Agenten: **Abnahme-Punkte** (Format Buchstaben+Ziffern, z. B. `P1`, `P2`)

**Ablage:** im Kern-Repo `docs/specs/<thema>.md`, für Agenten-Aufträge als Zieldokument `hydrahive2-modules/ziele/<thema>.md` – committen und pushen. Vorgabe des Nutzers geht vor.

Bei einer **kleinen Änderung** deckt das kurze Design dieselben Punkte in je ein, zwei Zeilen ab und geht ohne Bauherren-Prüfung direkt an den Nutzer.

**Bauherren-Prüfung** (bei einem Projekt): Lass `hydrahive-reviewer` oder den Projekt-Agenten (`ask_agent`, task_type `review`, `goal` + `deliverable`, nur lesen) das Design als die Person lesen, die es bauen soll – ohne mit dir reden zu können:

> „Du bist erfahrene Entwicklerin für HydraHive und sollst nach `<pfad>` einen Plan machen, ohne mit der Autorin reden zu können. Nenne nur die Fragen, die du vor einem guten Plan noch beantwortet brauchst: Stellen, an denen du raten müsstest und ein falscher Tipp etwas ausmacht. Je Frage: die Frage und warum die Antwort den Plan ändert, nach Wichtigkeit. Lass weg, was das Dokument ausdrücklich der Umsetzung überlässt oder was du selbst vernünftig entscheiden kannst, und Formulierungs-Kleinkram. Ist nichts Wichtiges offen: ‚nichts Wichtiges offen‘.“

Sag dem Nutzer vorher, dass ein Reviewer es zuerst liest und du einmal mit ein paar Fragen zurückkommen könntest. **Das Design erst übergeben, wenn die Prüfung zurück ist** – nicht vorlegen und die Prüfung nachschieben. Die Fragen in drei Stapel sortieren:
- **Schon beantwortet** durch Gespräch oder Projekt → Antwort ins Dokument.
- **Klein** – vernünftig entscheidbar, ohne zu ändern, was gebaut wird → selbst entscheiden, im Dokument als deine Entscheidung markieren.
- **Seine** – nur er kann sie beantworten, und die Antwort ändert, was gebaut wird.

Den Stapel „seine“ in **einer** Nachricht bringen, das Wichtigste zuerst. Mit seinen Antworten das Dokument ergänzen und es übergeben, mit einer kurzen Liste deiner Entscheidungen zum Gegenlesen. Das ist die einzige Fragerunde der Prüfung. Ohne Agenten: das Dokument selbst als diese Entwicklerin lesen.

## Harte Grenze

**Gebaut wird erst, wenn der Nutzer das Design freigegeben hat** – das kurze bei einer kleinen Änderung, das ausführliche bei einem Projekt. Bauen heißt: Produktcode schreiben, Gerüst anlegen, Abhängigkeiten installieren, Projekte/Branches anlegen, einen Agenten mit Umsetzung beauftragen. Lesen und Erkunden ist erlaubt.

Zwei Ausnahmen: Hat er auf die Fragen verzichtet, ist der Skill fertig und die Grenze fällt weg. Ein Spike, dem er zugestimmt hat, darf gebaut werden – bleibt aber Wegwerf; ihn zu behalten ist eine neue Anfrage, die wieder durch diese Grenze geht.

Nach der Freigabe kommt der Plan: Skill `writing-plans` laden, keinen anderen.

## Warnzeichen

| Gedanke | Wirklichkeit |
|---|---|
| „Ich biete eine Auswahl an, was er wollen könnte“ | Optionen lenken. Erst beschreiben lassen. |
| „Ich setze vernünftige Standardwerte“ | Gut – aber laut sagen. Einen Standard, den er nie gehört hat, kann er nicht ablehnen. |
| „Fragen beantwortet, ich schreib das Design“ | Erst die Ansätze, in einer eigenen Nachricht. |
| „Ich erkläre erst den Ablauf“ | Stell deine Frage. Der Ablauf zeigt sich von selbst. |
| „Er hat ‚klingt gut‘ zur Idee gesagt“ | Freigabe gilt für das, was du gezeigt hast. Ein Design, das du nicht geschrieben hast, ist nicht freigegeben. |
| „Der Spike läuft, ich bau darauf weiter“ | Behalten ist eine neue Anfrage. Zurück durch die Grenze. |
| „Ich frag lieber nach, wo die Datei hin soll“ | Ablauf-Fragen entscheidest du selbst und sagst es. |
