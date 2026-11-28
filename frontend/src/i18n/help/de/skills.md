# Skills — Wissen und Anleitungen für deine Agenten

## Was ist das?

Ein **Skill** ist eine wiederverwendbare **Anleitung**, die ein Agent bei Bedarf
lädt. Statt einem Agenten jedes Mal aufs Neue zu erklären, *wie* er etwas tun
soll („so machst du ein Code-Review", „so schreibst du eine Commit-Nachricht"),
schreibst du das einmal als Skill auf. Der Agent zieht sich diese Anleitung dann
selbstständig heran, wenn die Situation passt.

Denk an ein Skill wie an einen **Spickzettel** oder eine **Checkliste**, die im
Regal liegt und im richtigen Moment aufgeschlagen wird.

## Warum ist das nützlich?

- **Konsistenz**: Der Agent macht eine Aufgabe jedes Mal gleich (nach deiner
  Vorgabe), nicht mal so, mal so.
- **Weniger wiederholen**: Du musst dein Vorgehen nicht in jedem Gespräch neu
  erklären.
- **Kontext sparen**: Der Skill wird nur geladen, wenn er wirklich gebraucht wird
  — er belastet den Agenten nicht ständig.

## Arten von Skills

Auf der Skills-Seite stehen zwei Abschnitte:

- **Eigene Skills** — die du selbst anlegst und pflegst.
- **System-Skills** — mitgelieferte Skills, die HydraHive selbst installiert. Alle können sie lesen, ändern oder löschen dürfen nur Admins.

Dazu kommen die **Projekt-Skills**: eine gemeinsame Bibliothek eines Projekts, die du im Projekt findest. Alle Agenten, die in diesem Projekt arbeiten, sehen sie. Der Projekt-Agent kann sie selbst anlegen, oder du legst sie dort an.

## Mitgelieferte Skills

Die System-Skills sind fertig nutzbar. Ein Teil davon sind **Arbeitsweisen**, die einem Agenten beibringen, *wie* er eine Aufgabe angeht. Sie folgen den Arbeitsabläufen von Superpowers, einer frei nutzbaren Sammlung von Arbeitsweisen für KI-Agenten:

- **brainstorming** — erst verstehen, dann bauen: selbst nachlesen, nur Fragen stellen, deren Antwort etwas ändert, Ansätze mit Empfehlung vorlegen und den Entwurf freigeben lassen.
- **writing-plans** — aus einer Spec einen Umsetzungsplan machen, in kleinen Aufgaben mit eigenem Test, und vor dem Bauen freigeben lassen.
- **debugging** — Fehler systematisch suchen: erst die Ursache belegen, dann beheben. Nach drei gescheiterten Versuchen die Lösung grundsätzlich hinterfragen.
- **verification-before-completion** — bevor etwas als „fertig“ gilt: frisch ausführen, die Ausgabe lesen, das Ergebnis prüfen.
- **code-review** und **receiving-code-review** — eine Prüfung durchführen, und Prüfbefunde prüfen, statt sie blind umzusetzen.
- **dispatching-parallel-agents** — Aufträge an andere Agenten sauber zuschneiden und parallel vergeben.
- **finishing-development-branch** — einen fertigen Arbeitszweig ordentlich abschließen.
- **test** — Tests schreiben, einschließlich der Regel, dass ein neuer Test erst rot sein muss.
- **using-superpowers** — erklärt den Agenten, wann sie einen Skill laden sollen.

Dazu kommen Skills für den Alltag: **git-workflow**, **project-management**, **docs**, **refactor**, **security-audit**, **performance-profile**, **hh-review**, **code-graph**, **document-reading**, **generate-music**, **generate-speech**, **medical-akte**, **medical-research** und **skill-catalog**.

Beim Start von HydraHive werden fehlende System-Skills installiert und ältere Fassungen auf den neuen Stand gebracht. Hat ein Admin einen System-Skill selbst geändert, bleibt seine Fassung stehen.

## Wie ein Agent zu seinem Skill kommt

Ein Agent sieht nicht ständig alle Skills. Er lädt sie bei Bedarf:

- **Klassisch:** Im Systemprompt steht eine Tabelle der verfügbaren Skills mit ihrem **Wann nutzen?**. Passt einer, lädt der Agent ihn mit `load_skill`.
- **Werkzeuge bei Bedarf suchen:** Ist dieser Schalter im Reiter **Was darf der Agent?** an (siehe Hilfe zu *Agenten*), steht die lange Tabelle nicht mehr im Prompt. Der Agent sucht den passenden Skill mit `find_skills` in eigenen Worten (zum Beispiel „Fehler im Code suchen“) und lädt ihn dann mit `load_skill`. `find_skills` liefert Name und Kurzbeschreibung. Gesucht wird nur unter den Skills, die dieser Agent ohnehin hat: nie Skills anderer Nutzer oder Projekte.
- **Angeheftete Skills:** Skills, die du in der Expertenansicht des Agenten anheftest, stehen auch im Katalog-Modus fest im Prompt, damit der Agent sie sofort kennt.

Du musst dafür nichts einstellen. Entscheidend ist, dass **Wann nutzen?** klar beschreibt, in welcher Situation der Skill gebraucht wird, denn danach sucht und wählt der Agent.

## Die Felder eines Skills

- **Name** — Kurzbezeichnung (nur `a-z`, `0-9`, `_`, `-`). **Achtung:** kann nach
  dem Anlegen **nicht mehr geändert** werden.
- **Beschreibung** — worum es im Skill geht (eine Zeile).
- **Wann nutzen?** — der wichtigste Teil: ein Satz, der der KI sagt, **in welcher
  Situation** sie diesen Skill laden soll. Beispiel: *„Wenn der User um ein
  Code-Review bittet."* Je klarer, desto zuverlässiger greift der Agent zum
  richtigen Skill.
- **Benötigte Tools** — kommagetrennte Liste von Werkzeugen, die der Skill
  voraussetzt (optional).
- **Anweisungen (Markdown)** — der eigentliche Inhalt: die Schritt-für-Schritt-
  Anleitung, die der Agent beim Laden bekommt.
- **Quellen / URLs** — optionale Adressen (Foren, APIs, Dokus), die der Agent im
  Rahmen des Skills abrufen darf. Braucht eine Quelle Zugangsdaten, gibst du den
  Namen eines **Credential-Profils** an (siehe Hilfe zu *Credentials*) — die Auth
  wird dann automatisch eingehängt.

## Schritt-für-Schritt: Skill anlegen

1. **Neuer Skill** klicken.
2. **Name** vergeben (gut überlegen — unveränderlich!).
3. **Beschreibung** und vor allem **„Wann nutzen?"** ausfüllen — das entscheidet,
   ob der Agent den Skill im richtigen Moment findet.
4. Unter **Anweisungen** die eigentliche Anleitung schreiben (Markdown: Listen,
   Überschriften, Codeblöcke sind erlaubt).
5. Optional **benötigte Tools** und **Quellen** ergänzen.
6. Speichern.

## Skills pro Agent an-/ausschalten

Bei einem Agenten gibt es einen **Skills-Reiter**: dort siehst du, welche Skills
für diesen Agenten verfügbar sind, und kannst sie einzeln **an/aus** schalten.
So bekommt jeder Agent genau die Anleitungen, die zu seiner Rolle passen. Im Agenten-Reiter steht außerdem, wie viele Skills für diesen Agenten verfügbar sind. Mit **Bearbeiten** öffnest du einen Skill direkt von dort.

## Typische Fehler

- **Agent lädt den Skill nie** — Das Feld **„Wann nutzen?"** ist zu vage. Formulier
  es konkret und situationsbezogen.
- **„Name ungültig"** — Nur `a-z`, `0-9`, `_`, `-`, max. 50 Zeichen.
- **Name falsch gewählt** — Er lässt sich nachträglich nicht ändern; im Zweifel
  neu anlegen und den alten löschen.
- **Quelle nicht erreichbar** — Braucht die URL einen Login, muss ein passendes
  **Credential-Profil** hinterlegt und im Skill angegeben sein.

## Tipps

- **Ein Skill = ein Zweck.** Lieber mehrere kleine, klar benannte Skills als einen
  überladenen.
- **„Wann nutzen?" ist das Herzstück** — investier hier die meiste Sorgfalt.
- **Markdown nutzen**: Nummerierte Schritte und Checklisten machen die Anleitung
  für den Agenten am zuverlässigsten befolgbar.
- **System-Skills als Vorlage** ansehen, um ein Gefühl für guten Aufbau zu
  bekommen. Gute Beispiele sind **brainstorming**, **debugging** und **writing-plans**.

*Stand: HydraHive 2.0.0, 28.11.2026*
