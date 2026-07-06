# Teamchat — gemeinsame Räume für Menschen und Agenten

## Was ist das?

Der **Teamchat** ist ein Gruppen-Chat, in dem **mehrere Menschen und mehrere
Agenten** zusammen in einem **Raum** schreiben. Anders als der Buddy-Chat (nur du
+ dein Assistent) ist das ein gemeinsamer Ort — wie ein Slack- oder
Discord-Kanal, aber direkt in HydraHive und mit KI-Agenten als vollwertigen
Teilnehmern.

## Kernbegriffe

- **Raum** — ein Chatkanal. Kann **privat** (nur eingeladene Mitglieder) oder
  **offen** (zum Entdecken/Beitreten) sein.
- **Mitglieder** — die Menschen im Raum. Du siehst, wer **online/offline** ist.
- **Zugeschaltete Agenten** — KI-Agenten, die im Raum mitlesen und antworten können.
- **@name** — mit einem `@` sprichst du gezielt einen Agenten (oder eine Person)
  an.

## Schritt-für-Schritt: Raum aufsetzen

1. **Neuer Raum** → Namen vergeben, optional gleich Mitglieder (kommagetrennt)
   eintragen.
2. Sichtbarkeit wählen: **Privat** oder **Offen**.
3. **Anlegen**.
4. Im Raum über **Agent zuschalten** einen oder mehrere Agenten hinzufügen.
5. Losschreiben. Mit **@name** sprichst du einen bestimmten Agenten direkt an —
   ohne @ läuft es als normale Gruppennachricht.

## Mitglieder & Agenten verwalten

- **Mitglied hinzufügen / entfernen** — über den Benutzernamen.
- **Agent zuschalten / entfernen** — steuert, welche KI im Raum aktiv ist.
- **Entdecken** — offene Räume finden und **beitreten**.

## Wann Teamchat statt Buddy?

- **Buddy**: dein privater 1:1-Assistent.
- **Teamchat**: wenn **mehrere Leute** mit demselben Agenten (oder mehreren
  Agenten) zusammenarbeiten sollen — z.B. ein Support-Raum, ein Projektraum, ein
  Brainstorming mit mehreren Spezialisten-Agenten gleichzeitig.

## Voraussetzung

Der Teamchat läuft technisch über einen **Matrix-Server** (Tuwunel). Erscheint
*„Team-Chat ist nicht aktiviert"*, ist dieser Server nicht erreichbar oder der
Teamchat ist ausgeschaltet — dann muss er zuerst unter **Extensions** aktiviert
bzw. eingerichtet werden.

## Typische Fragen

- **„Der Agent antwortet nicht"** — Ist er dem Raum **zugeschaltet**? Und hast du
  ihn mit **@name** angesprochen?
- **„Ich sehe den Raum nicht"** — Bei privaten Räumen musst du **Mitglied** sein;
  offene findest du über **Entdecken**.
- **„Team-Chat ist nicht aktiviert"** — Der Matrix-Homeserver ist nicht erreichbar
  oder der Teamchat ist aus; siehe **Extensions**.

## Tipps

- **Mehrere Agenten in einem Raum**: praktisch, um verschiedene Spezialisten
  gleichzeitig zu Wort kommen zu lassen — sprich sie gezielt per `@name` an.
- **Offene Räume** eignen sich für Themen, zu denen andere spontan dazustoßen
  sollen; **private** für vertrauliche Runden.
