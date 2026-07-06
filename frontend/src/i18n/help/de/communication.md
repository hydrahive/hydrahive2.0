# Kommunikation — Messenger, die deinen Agenten erreichen

## Was ist das?

Auf dieser Seite verbindest du **externe Messenger** mit HydraHive, damit du
deinen persönlichen (Master-)Agenten auch **von unterwegs** erreichst — ohne die
Weboberfläche zu öffnen. Schreibst du z.B. auf WhatsApp, landet die Nachricht
direkt bei deinem Agenten, und seine Antwort kommt auf demselben Weg zurück.

Kurz: Dein Agent bekommt ein „Telefon", über das du ihm schreiben kannst.

## Verfügbare Kanäle

- **WhatsApp** — eingehende Nachrichten gehen direkt an deinen Master-Agenten.
- **Discord** — Direktnachrichten (DMs) und **@Erwähnungen** gehen an deinen
  Master-Agenten.

(Welche Kanäle einsatzbereit sind, hängt von deiner Installation und den
hinterlegten Zugangsdaten ab.)

## Wozu ist das gut?

- Du kannst deinem Agenten **von unterwegs** Aufgaben geben („Fass mir die Mails
  zusammen", „Wie läuft der Server?").
- Der Agent kann dich **proaktiv benachrichtigen** (z.B. über eine Butler-Automation,
  die eine Discord-Nachricht postet).
- Kein ständiges Einloggen im Browser nötig — der vertraute Messenger reicht.

## Zusammenspiel mit anderen Bereichen

- **Butler**: Die eingehenden Nachrichten können als **Trigger** für Automationen
  dienen („Wenn Discord-Nachricht mit … → Agent antworten lassen").
- **Credentials**: Für die Anbindung mancher Dienste werden Tokens/Zugänge
  gebraucht — die liegen unter *Credentials* bzw. in den System-Einstellungen.

## Typische Fragen

- **„Meine WhatsApp-Nachricht kommt nicht an"** — Die Anbindung ist nicht
  vollständig eingerichtet (Zugang/Token fehlt oder ist abgelaufen). Prüfe die
  Verbindungseinstellungen des Kanals.
- **„Discord: Agent reagiert nicht auf normale Nachrichten"** — Standardmäßig
  reagiert er auf **DMs** und **@Erwähnungen**. Sprich ihn direkt an.

## Tipps

- **Fang mit einem Kanal an** (z.B. Discord), bis der Weg zuverlässig läuft, bevor
  du weitere anbindest.
- **Kombiniere mit Butler**, wenn du automatische Reaktionen auf eingehende
  Nachrichten möchtest.
