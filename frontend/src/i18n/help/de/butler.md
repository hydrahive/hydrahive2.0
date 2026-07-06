# Butler — Automationen ohne Programmieren

## Was ist das?

Der **Butler** ist dein Automatisierungs-Baukasten. Du baust auf einer Fläche
per **Ziehen und Verbinden** von Knoten eine Regel zusammen: *„Wenn X passiert,
und Y zutrifft, dann tue Z."* Kein Code — du steckst die Bausteine wie ein
Flussdiagramm zusammen.

Beispiel: *„Wenn eine E-Mail von meinem Chef kommt (Trigger), und sie das Wort
‚dringend' enthält (Bedingung), dann lass Agent ‚Assistent' antworten (Aktion)."*

Eine solche Regel heißt **Flow**. Du kannst mehrere Flows haben, jeden einzeln
**aktiv** oder **inaktiv** schalten.

## Die drei Bausteine

Ein Flow liest sich immer von links nach rechts: **Trigger → Bedingung(en) →
Aktion(en)**. Nur der Trigger ist Pflicht — Bedingungen sind optional.

### 1. Trigger (der Auslöser — „Wenn …")

Womit soll es losgehen?

- **Nachricht empfangen** — eine eingehende Nachricht an einen Agenten.
- **Webhook empfangen** — ein externer Dienst ruft eine URL auf (du bekommst eine
  Hook-URL zum Kopieren).
- **Heartbeat ausgelöst** — zeitgesteuert/wiederkehrend (für regelmäßige Aufgaben).
- **Git-Ereignis** — z.B. ein Push oder eine Änderung in einem Repository.
- **Discord-Ereignis** — z.B. eine Reaktion oder Nachricht in einem Kanal.
- **E-Mail empfangen** — eine eingehende E-Mail.

### 2. Bedingungen (die Filter — „… und wenn zutrifft …")

Verfeinern, wann der Flow wirklich greifen soll. Jede Bedingung hat einen
**Ja/Nein**-Ausgang:

- **Zeitfenster** / **Wochentag** — nur zu bestimmten Zeiten.
- **Kontakt bekannt** — nur von bekannten Absendern.
- **Nachricht enthält** / **Feld enthält** — Textfilter auf Inhalt.
- **Git: Branch / Autor / Aktion ist …** — Filter auf Git-Ereignisse.
- **E-Mail: Absender / Betreff / Text enthält …** — Filter auf E-Mails.
- **Discord: Ereignis-Typ / Emoji ist …** — Filter auf Discord.

### 3. Aktionen (das Ergebnis — „… dann tue …")

Was soll passieren?

- **Agent antworten lassen** — ein Agent bearbeitet die Nachricht frei.
- **Agent mit Anweisung** — Agent antwortet, geführt durch deine Vorgabe.
- **Feste Antwort** — immer derselbe vordefinierte Text.
- **In Warteschlange** / **Ignorieren** — zur späteren Bearbeitung ablegen oder
  verwerfen.
- **Weiterleiten** — an einen anderen Agenten geben.
- **HTTP POST** — eine externe URL aufrufen (mit JSON-Body).
- **E-Mail senden**.
- **Git: Issue anlegen / Kommentar** — im Repository etwas erzeugen.
- **Discord posten** — Nachricht in einen Kanal schreiben.

## Schritt-für-Schritt: Ersten Flow bauen

1. Ziehe einen **Trigger** aus der Palette (links) auf die Fläche.
2. Ziehe eine **Aktion** dazu und **verbinde** beide (vom Ausgangspunkt des
   Triggers zum Eingang der Aktion ziehen).
3. Optional: eine **Bedingung** dazwischenhängen — verbinde ihren **Ja**-Ausgang
   mit der Aktion.
4. Klicke einen Knoten an → rechts im **Eigenschaften-Panel** die Details setzen
   (z.B. welcher Agent, welcher Kanal, welcher Textfilter).
5. Gib dem Flow oben einen **Namen** und klicke **Speichern**.
6. Teste gefahrlos mit **Probelauf**: der Flow wird mit einem Test-Ereignis
   durchgespielt — es werden **keine echten Aktionen** ausgeführt. Du siehst, ob
   der Trigger zutrifft und wie viele Aktionen laufen würden.
7. Wenn alles passt: den Flow auf **Aktiv** schalten.

## Typische Fehler

- **„Noch nicht aktiv — kein Backend-Event-Sender vorhanden"** — Der gewählte
  Trigger ist in deiner Installation (noch) nicht mit einer echten Ereignis-Quelle
  verbunden. Der Flow speichert zwar, feuert aber nicht, bis die Quelle existiert.
- **„Flow zuerst speichern, dann Probelauf"** — Probelauf geht nur mit einem
  gespeicherten Flow.
- **Aktion läuft nie** — Prüfe die **Verbindungen**: ist der Trigger wirklich mit
  der Aktion verbunden? Bei Bedingungen: hängt die Aktion am **Ja**-Ausgang?
- **Discord-Kanal fehlt** — Du brauchst die **numerische Kanal-ID** (in Discord:
  Rechtsklick auf den Kanal → ID kopieren).

## Tipps

- **Erst Probelauf, dann aktiv.** Der Probelauf ist gefahrlos — nutze ihn immer,
  bevor du scharf schaltest.
- **Klein anfangen**: Trigger + eine Aktion. Bedingungen später ergänzen.
- **Mehrere Flows** statt eines Riesen-Flows — pro Zweck einer, einzeln
  ein-/ausschaltbar, viel übersichtlicher.
- **Projekt-Kontext**: Flows gehören zum aktuellen Projekt — achte darauf, im
  richtigen Projekt zu sein.
