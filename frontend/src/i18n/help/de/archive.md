# Archiv & Sicherung – Gelöschtes aufbewahren statt verlieren

Das System-Archiv ist der Ort, an dem HydraHive gelöschte Agenten, Projekte und Nutzer als geprüfte Pakete aufhebt.
So geht beim Löschen nichts aus Versehen verloren. Das Archiv lässt sich im Netz als Freigabe öffnen und auf Wunsch
zusätzlich auf einen anderen Server (NAS) kopieren. Die Seite ist für Admins.

## So startest du

1. Öffne das Admin-Cockpit und klicke unter **Verwaltung** auf **Archiv**. Es öffnet sich das Fenster
   **Archiv & Sicherung**.
2. Du musst nichts einrichten. HydraHive legt den Archiv-Ordner und die Netzwerk-Freigabe selbst an. Im Reiter
   **Speicher** steht beim **Speicherort** dann **Bereit**.
3. Lösche einen Agenten, ein Projekt oder einen Nutzer und wähle im Lösch-Fenster **Ins Archiv (empfohlen)**.
   Danach steht das Paket im Reiter **Inhalt**.

## Was du damit machen kannst

### Löschen mit Archiv

Beim Löschen eines Agenten, Projekts, Nutzers oder einer externen Instanz fragt HydraHive nach dem Weg:

- **Ins Archiv (empfohlen)**: HydraHive packt alles in ein Paket, prüft es und löscht erst danach. Der Weg ist
  gesperrt, wenn im Archiv nicht genug Platz frei ist oder das Archiv gerade umzieht. Den Grund zeigt das Fenster an.
- **Unwiderruflich löschen**: ohne Sicherung. Zur Bestätigung musst du den Namen genau eintippen.

Vorher zeigt das Fenster, was betroffen ist: Größe, mitgelöschte Projekte und Agenten, Zahl der Chats und den freien
Platz im Archiv. Eingehängte Laufwerke werden ausgehängt und nicht mitgepackt. VMs, Container und SMB-Verbindungen
bleiben bestehen. Wird ein Nutzer gelöscht, gehen seine Agenten in fremden Projekten an den Ersteller des jeweiligen
Projekts. Den letzten Admin kann man nicht löschen.

Mit **Ins Archiv und löschen** startet der Vorgang. Er läuft im Hintergrund weiter, du kannst das Fenster schließen.

### Was im Archiv landet

- **Agent**: Agenten-Ordner mit Gedächtnis, eigener Arbeitsordner und seine Chats.
- **Projekt**: Projekt-Ordner, Arbeitsordner, die Agenten des Projekts und die Chats.
- **Nutzer**: Konto, Zugangsdaten, Skills, Butler-Abläufe, Chats und die Agenten des Nutzers. Jedes eigene Projekt
  bekommt ein eigenes Projekt-Paket.

Passwörter und Tokens in den Einstellungen von Agenten und Projekten ersetzt HydraHive im Paket durch `***`.
Neben jedem Paket (`.tar.gz`) liegt eine Begleitdatei (`.json`) mit Name, Art, Besitzer, Grund, Datum, Größe und
Prüfsumme.

### Reiter „Speicher“

- **Speicherort** zeigt, ob das Archiv **Bereit** ist, **Nicht beschreibbar** oder **Fehlt**. Dazu kommen Ordner,
  Platte, freier Platz, Zahl der Pakete, belegter Platz und die Größe des Papierkorbs.
- **Leeren** leert den **Papierkorb**. Dazu öffnet sich **Papierkorb endgültig leeren**. Erst wenn du das Wort
  „Papierkorb“ eintippst, geht **Endgültig leeren**.
- **Ort wechseln** öffnet **Archiv-Ort wechseln** (siehe unten).
- **Netzwerk-Freigabe**: Das Archiv lässt sich im Windows-Explorer oder Finder öffnen, zum Lesen und Schreiben.
  **Adresse**, **Benutzer** und **Passwort** stehen zum Kopieren da. Mit **Netzwerk-Freigabe anbieten** schaltest du
  sie aus und an. Ist Samba nicht installiert, gibt es den Knopf **Samba einrichten**. Das Archiv selbst funktioniert
  auch ohne Freigabe.
- **Externer Server (NAS)**: zusätzliche Kopie auf einem anderen Rechner (siehe unten).

### Archiv-Platte wählen

Standardmäßig liegt das Archiv bei den Projektdaten auf derselben Platte. Unter **Ort wechseln** wählst du einen
anderen Ort:

- Zur Wahl stehen **Standard (bei den Projektdaten)** und beschreibbare lokale Platten mit Linux-Dateisystem.
  System-Ordner bietet HydraHive nicht an. Ein freies Pfadfeld gibt es nicht.
- Auf der gewählten Platte legt HydraHive einen Ordner `hydrahive-archiv` an.
- Passt ein Ort nicht, steht der Grund darunter, zum Beispiel „Dort liegen schon Dateien.“ oder „Nicht genug Platz.“
- Darf HydraHive auf der Platte noch nicht schreiben, hilft **Platte für HydraHive einrichten**.
- **Umziehen** kopiert alle Pakete, Handablagen und den Papierkorb und prüft die Kopie. Erst dann stellt HydraHive
  um und löscht am alten Ort. Geht dabei etwas schief, bleibt das Archiv unverändert am alten Ort. Während des Umzugs
  ruht die Netzwerk-Freigabe, und **Ins Archiv (empfohlen)** ist gesperrt.

### Reiter „Vorgänge“

- **Laufende Vorgänge** zeigt den laufenden Lösch-Auftrag mit Fortschritt, wartende Aufträge und die letzten
  Ergebnisse. Es läuft immer nur ein Auftrag zur Zeit.
- **Waisen** findet Arbeitsordner ohne Agent und Agenten, deren Projekt es nicht mehr gibt. **Aufräumen** entfernt
  leere Ordner. Alles mit Inhalt kommt vorher ins Archiv.

### Reiter „Inhalt“

**Archivierte Elemente** listet alle Pakete mit Name, Art, Besitzer, Grund, Datum, Server-Stand und Größe. Über die
Auswahl **Alle Arten** filterst du nach Art. Dateien, die jemand über die Freigabe ohne Begleitdatei abgelegt hat,
stehen als **Von Hand abgelegt** in der Liste.

### Prüfung und Wiederherstellen

Jedes Paket wird nach dem Packen vollständig neu gelesen. HydraHive vergleicht die Prüfsumme, liest das Paket bis zum
Ende und zählt die Einträge. Erst wenn alles stimmt, wird gelöscht. Ist das Paket fehlerhaft, wird es verworfen und
nichts gelöscht.

Wird HydraHive mitten in einem Auftrag neu gestartet, setzt es vor dem Löschschritt alles zurück. War das Löschen
schon im Gang, löscht es zu Ende, denn die Daten liegen dann geprüft im Archiv.

Einen Knopf zum Wiederherstellen gibt es nicht. Die Pakete sind gewöhnliche `.tar.gz`-Dateien. Über die
Netzwerk-Freigabe kannst du sie kopieren und selbst öffnen.

### Entfernte Ablage auf einem NAS

Unter **Externer Server (NAS)** trägst du eine Windows- bzw. SMB-Freigabe ein: **Server**, **Freigabe**, optional
**Unterordner**, **Benutzer** und **Passwort**. Bleibt der Benutzer leer, meldet sich HydraHive als Gast an.

1. **Speichern**, dann **Verbindung testen**.
2. Erst nach einem erfolgreichen Test lässt sich **Kopie auf den Server** einschalten. Änderst du später die
   Daten, musst du neu testen.
3. Ab dann kopiert HydraHive jedes neue Paket auf den Server, liest es von dort zurück und vergleicht die Prüfsumme.
   Die Kopie hier bleibt erhalten.

- Ist der Server nicht erreichbar, geht Löschen trotzdem. HydraHive versucht es von selbst wieder: nach 1, 5 und
  30 Minuten, danach stündlich.
- **Jetzt abgleichen** schickt alles, was auf dem Server fehlt oder anders ist, in die Kopier-Reihe, auch Dateien,
  die von Hand abgelegt wurden.
- Die Übersicht zeigt **Pakete auf dem Server**, **Warten auf Kopie** und **Nur auf dem Server**. In der Liste steht
  je Paket „auf dem Server“, „wartet“, „nur hier“ oder „nur auf dem Server“.
- **Lokale Kopie löschen** (je Paket im Reiter **Inhalt** oder für alle über „Alle lokalen Kopien löschen“) gibt
  Platz frei. Das geht nur für Pakete, die geprüft auf dem Server liegen. Vor dem Löschen liest HydraHive jedes Paket
  noch einmal vom Server und vergleicht es. Stimmt etwas nicht, bleibt das Paket hier und wird neu hochgeladen.

## Gut zu wissen

- Papierkorb: Was über die Netzwerk-Freigabe gelöscht wird, landet im Papierkorb des Archivs. Er wird nie von
  selbst geleert, nur über **Leeren** mit dem Bestätigungswort.
- Chats: Gelöschte Chats verschwinden aus HydraHive. Beim Weg **Ins Archiv (empfohlen)** liegen sie im Paket. Das Datamining
  behält seine Kopie.
- System-Backup: Das Archiv ist nicht Teil des **System-Backup** auf der Seite System. Ein eingespieltes Backup
  ersetzt das Archiv nicht.
- Arten im Filter: Der Filter kennt auch die Arten „System-Backup“ und „Ablage“. HydraHive selbst legt dort
  nichts ab. Dort steht nur, was über die Freigabe von Hand hineinkommt.
- Agenten: Agenten haben kein Werkzeug für das Archiv und können nichts ins Archiv löschen.
- Rechte: Das Archiv-Fenster und das Löschen von Agenten, Projekten und Nutzern sind Admins vorbehalten.
- Passwort des NAS: Es wird verschlüsselt gespeichert und nie wieder angezeigt. Leer lassen behält das
  gespeicherte Passwort.
- Nicht verwechseln mit dem Modul „Archiver“: Der Archiver ist ein eigenes Modul für USB-Festplatten am Server.
  Er kopiert Platten in ein Projekt und zurück und hat eine eigene Hilfe. Das System-Archiv hier gehört zu HydraHive
  selbst und hebt Gelöschtes auf.
- Projekt-Status: Der Status **Archiviert** in den Projekt-Einstellungen ist nur eine Markierung. Das Projekt
  kommt dadurch nicht ins System-Archiv.
- Typische Meldungen: „Im Archiv ist nicht genug Platz frei.“, „Das Archiv zieht gerade um.“, „Ein Netzlaufwerk
  ließ sich nicht aushängen. Damit dort nichts gelöscht wird, wurde abgebrochen.“ In all diesen Fällen wurde nichts
  gelöscht.

*Stand: HydraHive 2.0.0, 23.11.2026*
