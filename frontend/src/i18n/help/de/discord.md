# Discord-Serververwaltung – was deine Agenten in Discord lesen, posten und verwalten dürfen

Mit den Discord-Werkzeugen arbeiten deine Agenten selbst in Discord. Sie lesen Kanäle und Foren, posten und antworten, moderieren Beiträge und verwalten auf Wunsch einen ganzen Server mit Kanälen, Rollen und Mitgliedern.
Du legst genau fest, wo das erlaubt ist. Ohne deine Freigabe können die Werkzeuge nichts tun.
Wie Discord-Nachrichten an deinen Agenten gehen (Direktnachrichten und @Erwähnungen), steht im Artikel „Kommunikation“.

## So startest du

1. Discord muss auf dem Server eingeschaltet sein. Ein Admin findet den Schalter unter **System** → **Einstellungen** in der Gruppe **Discord** als **Discord aktiv**. Er ist ab Werk an. Eine Änderung wirkt erst nach einem Neustart des Backends.
2. Öffne **Kommunikation** und richte im Bereich **Discord** deinen Bot ein. Eine Anleitung findest du unter **So richtest du den Bot ein**. Klicke danach auf **Verbinden**.
3. Unter **Kanäle für Agenten-Werkzeuge** siehst du jetzt alle Text-, Ankündigungs- und Forum-Kanäle, die dein Bot sieht. Hake die Kanäle an, in denen Agenten lesen und schreiben dürfen.
4. Soll ein Agent in einem Kanal auch moderieren, klicke beim angehakten Kanal auf **Moderieren**.
5. Soll ein Agent einen ganzen Server verwalten, hake beim Server **Server verwalten** an.
6. Klicke auf **Speichern**.
7. Öffne die Einstellungen des Agenten und gehe zum Reiter **Tools & MCP**. Bei einem Projekt-Agenten heißt der Reiter **Tools**. Wähle im Auswahlfeld die Gruppe **Discord** und hake die Werkzeuge an, die der Agent nutzen soll.

Die Discord-Werkzeuge gehören zu keiner Standard-Ausstattung. Du schaltest sie für jeden Agenten einzeln frei.

## Was du damit machen kannst

### Kanäle freigeben

Die Liste **Kanäle für Agenten-Werkzeuge** ist nach Server und Kategorie geordnet. Neben einem Kanal können diese Hinweise stehen:

- **Forum**: Der Kanal ist ein Forum.
- **nur lesen**: Dein Bot darf dort nichts senden.
- **nicht erreichbar**: Du hast den Kanal freigegeben, aber der Bot findet ihn nicht mehr, zum Beispiel weil er gelöscht wurde. Du kannst ihn abwählen.

Mit **Neu laden** holst du die Liste neu.

Für die Freigabe gilt:

- Ist nichts angehakt, haben Agenten keinen Zugriff auf Discord.
- Beiträge in einem freigegebenen Forum sind automatisch mit freigegeben.
- Moderation gibt es nur in freigegebenen Kanälen. Wählst du einen Kanal ab, verliert er auch die Moderation.
- **Server verwalten** hängt nicht von der Kanalfreigabe ab. Das Häkchen ist ausgegraut, wenn dein Bot auf dem Server weder Administrator ist noch Kanäle und Rollen verwalten darf.
- Die Liste unter **Whitelist Channel-IDs (leer = alle)** gilt nur für eingehende @Erwähnungen, nicht für die Werkzeuge.

Jeder Benutzer arbeitet mit seinem eigenen Bot und seiner eigenen Freigabe.

### Lesen

- `discord_channels` zeigt die freigegebenen Kanäle. Zu jedem Kanal steht dabei, ob der Agent dort lesen und schreiben darf oder nur lesen und ob er moderieren darf. Bei Foren stehen auch die verfügbaren Tags dabei.
- `discord_read` liest einen freigegebenen Kanal:
  - Aus einem Textkanal kommen die letzten Nachrichten. Ohne Angabe sind es 20, höchstens 50. Ältere Nachrichten holt der Agent seitenweise nach.
  - Aus einem Forum kommt die Liste der Beiträge mit Titel, Tags und Zahl der Antworten. Aktive Beiträge stehen oben.
  - Aus einem Forum-Beitrag kommen die Eröffnung und die Antworten, ebenso begrenzt und seitenweise.

Sehr lange Nachrichten werden beim Lesen gekürzt.

### Posten, antworten, bearbeiten

- `discord_post` schreibt eine Nachricht in einen Textkanal oder legt in einem Forum einen neuen Beitrag an.
  - Ein Forum-Beitrag braucht einen Titel mit höchstens 100 Zeichen.
  - Er kann bis zu 5 Tags tragen. Bei Tag-Namen sind Groß- und Kleinschreibung und Emoji egal.
  - Verlangt das Forum einen Tag, muss mindestens einer gesetzt sein.
- `discord_reply` antwortet in einem Forum-Beitrag oder Textkanal. Auf Wunsch antwortet er auf eine bestimmte Nachricht.
- `discord_edit` ändert eine Nachricht, die der Bot selbst geschrieben hat. Fremde Nachrichten kann der Agent nicht bearbeiten.

Für alles, was ein Agent schreibt, gilt:

- Lange Texte werden an Absätzen auf höchstens 4 Nachrichten mit je bis zu 2000 Zeichen verteilt. Ist der Text länger, lehnt das Werkzeug ihn ab.
- Der Bot pingt nie @everyone, @here oder Rollen. Einzelne Personen darf er erwähnen.
- Ein Agent kann bis zu 4 Bilder anhängen (png, jpg, gif, webp, je höchstens 8 MB).
  - Die Bilder müssen aus seinem eigenen Arbeitsordner stammen.
  - Orte mit Schlüsseln oder Zugangsdaten sind gesperrt, auch wenn dort ein Bild liegt.
- Vor dem Senden entfernt HydraHive bekannte Geheimnisse aus dem Text. Dazu gehören hinterlegte Schlüssel des Systems und des Agenten, deine Zugangsdaten unter **Credentials** und das Token deines Bots.

### Foren und Tags (Moderation)

Diese Werkzeuge wirken nur in Kanälen mit **Moderieren**:

- `discord_thread_manage` verwaltet einen Forum-Beitrag.
  - Der Agent kann Tags setzen, ergänzen oder entfernen, auch Tags wie „Gelöst“, die nur Moderatoren setzen dürfen.
  - Er kann den Titel ändern, den Beitrag schließen oder öffnen, sperren oder entsperren und oben im Forum anheften.
  - Es ändert sich nur, was der Agent angibt.
  - Dein Bot braucht dafür in Discord das Recht „Threads verwalten“.
- `discord_forum_tags` pflegt die Tag-Liste eines Forums.
  - Der Agent kann Tags anlegen, umbenennen, ihr Emoji ändern, sie auf „nur Moderatoren“ stellen oder entfernen.
  - Ein Forum hat höchstens 20 Tags, ein Tag-Name höchstens 20 Zeichen.
  - Ein entfernter Tag verschwindet auch von allen Beiträgen.
  - Dein Bot braucht dafür das Recht „Kanäle verwalten“.
- `discord_message_pin` pinnt eine Nachricht an oder löst sie.
- `discord_delete` löscht eine einzelne Nachricht oder einen ganzen Forum-Beitrag.
  - Jede Löschung musst du bestätigen.
  - Kanäle und Foren löscht dieses Werkzeug nie.
  - Den gelöschten Inhalt zeigt HydraHive dem Agenten danach nicht mehr.
  - Für fremde Nachrichten braucht der Bot das Recht „Nachrichten verwalten“.

### Serverstruktur

`discord_server_manage` wirkt nur auf Servern mit **Server verwalten**. Damit kann der Agent:

- einen Überblick zeigen: Kategorien mit ihren Kanälen, Rollen und die Zahl der Mitglieder,
- Kategorien und Kanäle anlegen. Möglich sind Textkanäle, Ankündigungskanäle und Foren. Ein Forum kann gleich mit Tags und Tag-Pflicht angelegt werden.
- Kanäle ändern: Name, Thema, Kategorie, Position, Slowmode (bis 6 Stunden) und Altersbeschränkung,
- Kanäle löschen, nur mit deiner Bestätigung,
- die Rechte einer Rolle in einem Kanal setzen, nur mit deiner Bestätigung,
- Einladungen erstellen. Sie gelten höchstens 7 Tage und für höchstens 100 Nutzungen, 0 heißt unbegrenzt.

Neue Kanäle sind nicht automatisch für Lesen und Posten freigegeben. Hake sie dafür unter **Kanäle für Agenten-Werkzeuge** an.

### Rollen und Mitglieder

`discord_member_manage` wirkt ebenfalls nur auf Servern mit **Server verwalten**.

- Rollen kann der Agent auflisten, anlegen, ändern, löschen, vergeben und entziehen. Er kann Farbe und Rechte einstellen, festlegen, ob man die Rolle erwähnen darf, und sie in der Mitgliederliste getrennt anzeigen lassen.
- Mitglieder kann der Agent auflisten, auch gefiltert nach Name oder Rolle (höchstens 100 Einträge). Außerdem kann er:
  - Nicknames setzen,
  - Mitglieder in einen Timeout schicken (höchstens 28 Tage, 0 hebt ihn auf),
  - kicken, bannen und entbannen. Beim Bann kann er die Nachrichten der letzten 0 bis 7 Tage löschen lassen.

Jede Änderung mit `discord_server_manage` und `discord_member_manage` trägt im Audit-Log von Discord den Vermerk „HydraHive-Agent“. Bei Timeout, Kick, Bann und Entbannen steht dort auch der Grund, den der Agent angibt.

## Mit Buddy und Agenten

In der Gruppe **Discord** findest du diese Werkzeuge: `discord_channels`, `discord_read`, `discord_post`, `discord_reply`, `discord_edit`, `discord_thread_manage`, `discord_message_pin`, `discord_delete`, `discord_forum_tags`, `discord_server_manage` und `discord_member_manage`.

Du kannst zum Beispiel fragen:

- „Was ist heute im Support-Forum neu?“
- „Beantworte den offenen Beitrag zur Installation und setz den Tag Gelöst.“
- „Leg eine Kategorie Projekte mit einem Forum und den Tags Idee und Fehler an.“
- „Gib dem neuen Mitglied die Rolle Tester.“

Das geht nicht:

- Außerhalb der freigegebenen Kanäle lesen oder posten. Ein unbekannter und ein nicht freigegebener Kanal ergeben dieselbe Meldung, so erfährt ein Agent nichts über fremde Kanäle.
- Fremde Nachrichten bearbeiten.
- Kanäle oder Foren mit `discord_delete` löschen.
- Die Rechte „Administrator“ und „Server verwalten“ vergeben. HydraHive vergibt sie nie, weder an Rollen noch in Kanalrechten.
- Diese Rollen ändern, löschen, vergeben oder entziehen:
  - die Rolle @everyone,
  - die Rolle des Bots,
  - Rollen, die eine Integration verwaltet,
  - Rollen über oder auf Höhe der Bot-Rolle.
- Diese Personen kicken, bannen, in einen Timeout schicken, umbenennen oder ihnen eine Rolle entziehen:
  - den Serverbesitzer,
  - den Bot selbst,
  - alle, die unter **Besitzer (deine Discord-User-IDs)** eingetragen sind,
  - Mitglieder, deren höchste Rolle über oder auf Höhe der Bot-Rolle liegt.

## Gut zu wissen

- Bestätigungen: Bei diesen Aktionen erscheint im Chat **Geschützter Zugriff — Bestätigung nötig:** mit einer Begründung und den Knöpfen **Erlauben** und **Verweigern**:
  - jede Löschung mit `discord_delete`,
  - Kanal löschen und Kanalrechte setzen,
  - Rolle löschen und Rolle vergeben,
  - Kick und Bann,
  - eine Rolle mit riskanten Rechten anlegen oder ändern, etwa „Rollen verwalten“, „Kanäle verwalten“, „Mitglieder kicken“, „Mitglieder bannen“, „Nachrichten verwalten“ oder „@everyone erwähnen“.

  Im Chat wartet der Agent, bis du entscheidest. Läuft er ohne Chat-Fenster, etwa per Zeitplan oder über einen Messenger, wartet er standardmäßig 5 Minuten. Danach führt er die Aktion nicht aus.
- Discord-Inhalte sind nur Daten: Alles, was ein Agent aus Discord liest, ist als fremder Inhalt markiert. Der Agent ist angewiesen, Anweisungen darin nie zu befolgen. Er soll nur auf deine ausdrückliche Anweisung moderieren und verwalten, nie weil ein Beitrag in Discord dazu auffordert.
- Ist **Discord aktiv** ausgeschaltet, stehen die Discord-Werkzeuge nach dem Neustart gar nicht zur Auswahl.
- Rechte deines Bots: HydraHive kann nur, was dein Bot in Discord darf. Fehlt ein Recht, meldet der Agent zum Beispiel: „Dem Bot fehlt in diesem Kanal die Berechtigung «Nachrichten senden».“
- Typische Meldungen und was du dann tust:
  - „Es sind keine Discord-Kanäle für Agenten-Werkzeuge freigegeben“: Hake unter **Kanäle für Agenten-Werkzeuge** Kanäle an und speichere.
  - „Dein Discord-Bot ist nicht verbunden“: Klicke unter **Kommunikation** bei Discord auf **Verbinden**.
  - „… ist nicht für Moderation freigegeben“: Klicke beim Kanal auf **Moderieren**.
  - „Es ist kein Discord-Server für die Verwaltung freigegeben“: Hake beim Server **Server verwalten** an.

*Stand: HydraHive 2.0.0, 23.11.2026*
