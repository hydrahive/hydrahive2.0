# Vault – sensible Bereiche mit einer eigenen PIN schützen

Der Vault ist die Schutzzone für deine sensiblen Daten: Gesundheit, Geld, Rechtsfälle und Zugangsdaten. Diese
Bereiche öffnen sich in der Oberfläche erst, wenn du deine persönliche Vault-PIN eingibst. Auch deine Agenten
kommen nur an diese Daten, solange dein Vault entsperrt ist.

## So startest du

1. Öffne **Vault** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich **Zuhause & Privat**).
   Die Vault-Seite selbst ist ohne PIN offen. Sie lädt keine sensiblen Daten.
2. Klicke unter **Deine sensiblen Bereiche** auf einen Bereich, zum Beispiel **Zugangsdaten**.
3. Beim ersten Mal erscheint **Vault-PIN festlegen**. Gib dein **Login-Passwort** ein, dann eine **Neue PIN** aus 6
   bis 12 Ziffern und noch einmal unter **PIN wiederholen**. Klicke **Speichern**.
4. Der Bereich öffnet sich. Oben in der Kopfleiste steht jetzt „Entsperrt · noch … min“.

## Was du damit machen kannst

### Bereiche hinter dem Vault
- **Zugangsdaten** (API-Schlüssel und Passwörter) gehören immer dazu.
- Dazu kommen Module, die sich selbst als Vault-Bereich kennzeichnen: **Meine Akte**, **Cryptoboard**,
  **Haushaltsbuch** und das Modul „Recht“. Sie sind nur geschützt, wenn ein Admin sie installiert hat.
- Die Vault-Seite zeigt als Kacheln nur Bereiche, die installiert sind und die du nutzen darfst. Ist noch keines der
  Module installiert, steht dort „Noch keine sensiblen Module installiert.“
- Unter **Verlauf** findest du zusätzlich Links zu **Datamining** und **Gedächtnis**. Diese beiden Seiten sind nicht
  durch die PIN geschützt.

### Entsperren
- Öffnest du einen Vault-Bereich bei gesperrtem Vault, erscheint **Vault entsperren**. Gib deine **PIN** ein und
  klicke **Entsperren**. Die Seite lädt danach neu, jetzt mit deinen Daten.
- **Abbrechen** schließt das Fenster. Der Bereich bleibt dann gesperrt.

### Automatische Sperre
- Nach 15 Minuten ohne Nutzung eines Vault-Bereichs sperrt der Vault wieder von selbst. Jede Nutzung setzt die Uhr
  neu.
- Spätestens 8 Stunden nach dem Entsperren ist der Vault in jedem Fall wieder zu.
- Die Entsperrung gilt nur in diesem Browser-Tab. Schließt du den Tab, musst du im nächsten neu entsperren.

### Sofort sperren
- In der Kopfleiste steht der Zustand: **Gesperrt** oder „Entsperrt · noch … min“. Die Anzeige ist nur auf breiten
  Bildschirmen zu sehen und erscheint erst, wenn du eine PIN festgelegt hast.
- **Jetzt sperren** schließt den Vault sofort, auch in anderen Tabs und auf anderen Geräten und auch für deine
  Agenten. Die Seite lädt neu und fragt bei einem Vault-Bereich wieder nach der PIN.

### PIN vergessen
- Klicke im Fenster **Vault entsperren** auf **PIN vergessen?**. Gib dein **Login-Passwort** ein und lege eine neue
  PIN fest. Deine Daten bleiben erhalten.
- Ein Admin kann deine PIN unter **Benutzer** mit **Vault-PIN zurücksetzen** entfernen. Er erfährt dabei nie deine
  PIN und kann keine für dich festlegen. Du vergibst beim nächsten Öffnen selbst eine neue. Deine Daten bleiben
  erhalten.

## Mit Buddy und Agenten

Der Vault hat keine eigenen Werkzeuge. Er entscheidet aber, ob die Werkzeuge der sensiblen Bereiche Daten liefern.
Das betrifft zum Beispiel das Portfolio aus dem Cryptoboard, die Werkzeuge von **Meine Akte** und die Werkzeuge
des Moduls „Recht“.

- Vault entsperrt: Deine Agenten, auch dein Buddy, dürfen diese Werkzeuge benutzen. Für sie gilt dieselbe Uhr:
  15 Minuten seit der letzten Nutzung, höchstens 8 Stunden. Jede Nutzung durch einen Agenten setzt die 15 Minuten
  für die Agenten neu.
- Vault gesperrt: Das Werkzeug läuft gar nicht. Der Agent bekommt nur die Antwort „Vault gesperrt – bitte in
  HydraHive entsperren.“ Entsperren kannst nur du in der Oberfläche, nicht der Agent.
- Kanäle bekommen nie Vault-Daten. Kommt eine Anfrage über WhatsApp, Discord, E-Mail, Telegram oder einen
  anderen Kanal, liefert ein Vault-Werkzeug nichts, auch wenn dein Vault gerade offen ist. Das gilt auch für
  Spezialisten, die der Agent für diese Anfrage beauftragt. Der Agent erfährt dann zum Beispiel „Diese Daten gibt
  es nur in HydraHive, nicht über WhatsApp.“
- Allgemeine Werkzeuge wie Kurse von Kryptowährungen oder E-Mails lesen und senden sind keine Vault-Werkzeuge. Sie
  funktionieren unabhängig vom Vault.
- Zugangsdaten benutzen Agenten, ohne sie im Klartext zu sehen.

Das kannst du zum Beispiel fragen, wenn dein Vault entsperrt ist und das Cryptoboard installiert ist:
- „Wie steht mein Portfolio?“

## Gut zu wissen

- Die PIN besteht aus 6 bis 12 Ziffern. Gespeichert wird sie nur unkenntlich gemacht. Zum Festlegen oder Ändern
  brauchst du immer dein Login-Passwort.
- Nach 5 falschen PINs innerhalb von 15 Minuten musst du warten. Die Meldung lautet „Zu viele falsche PINs. Bitte in
  … Sekunden erneut versuchen.“
- Programme, die mit einem API-Schlüssel zugreifen, brauchen keine PIN. Die PIN schützt das Ansehen in der
  Oberfläche und die Werkzeuge der Agenten.
- Typische Meldungen:
  - „Vault gesperrt – bitte PIN eingeben.“: Der Vault ist zu, das PIN-Fenster öffnet sich.
  - „Falsche PIN.“: Die PIN stimmt nicht. Versuche es noch einmal oder nutze **PIN vergessen?**.
  - „Die beiden PINs stimmen nicht überein.“ oder „Die PIN muss aus 6 bis 12 Ziffern bestehen.“: Beim Festlegen
    stimmt die Eingabe nicht.
  - „Ungültige Zugangsdaten“: Das Login-Passwort beim Festlegen oder bei **PIN vergessen?** ist falsch.

*Stand: HydraHive 2.0.0, 23.11.2026*
