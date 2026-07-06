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

## Zwei Arten von Skills

- **Eigene Skills** — die du selbst anlegst und pflegst.
- **System-Skills** — mitgelieferte Vorlagen (z.B. für Code-Review, Debugging,
  Git-Workflow). Diese sind fertig nutzbar.

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
So bekommt jeder Agent genau die Anleitungen, die zu seiner Rolle passen.

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
  bekommen.
