# Buddy-Media-Player

## Was

Der Buddy erhält wieder einen echten, optionalen Media-Slot. In Phase B zeigt dieser Slot den vorhandenen kompakten Musicplayer des installierten Moduls. In Phase C wird das bestehende Musicplayer-Modul datenkompatibel zu einem Audio-/Videoplayer mit eigener Cockpit-Seite erweitert.

## Warum

Der Musicplayer wurde beim Buddy-Redesign nicht entfernt: Backend, zehn gespeicherte Tracks und `MusicPlayerBuddyBox` existieren weiterhin. Commit `35627cdc` entfernte jedoch den Konsum von `moduleBuddyWidgets` aus `BuddyPage` und ersetzte echte Widgets durch Links. Der Link `/musicplayer` hat derzeit kein Ziel, weil das Modul weder Route noch Navigation exportiert.

Das Redesign soll nicht pauschal zurückgerollt werden. Buddy bleibt primär Chat und Companion; nur explizit als Media-Widget registrierte Module dürfen den Media-Slot belegen.

## Phase B: optionaler Buddy-Media-Slot

### Modulvertrag

- Der Frontend-Modulgenerator sammelt den optionalen Export `buddyMediaWidgets` getrennt von den bestehenden allgemeinen `buddyWidgets`.
- Ein Media-Widget ist ein Deskriptor mit stabiler `id`, numerischer `order` und einer React-`component`.
- Der Core importiert kein optionales Modul direkt.
- Ungültige Deskriptoren werden ignoriert; gültige werden deterministisch nach `order` und `id` sortiert.
- Das Musicplayer-Modul registriert `MusicPlayerBuddyBox` mit `id: "musicplayer"`.

### Darstellung

- Der Media-Slot erscheint in der rechten Buddy-Spalte nur, wenn mindestens ein Media-Widget installiert ist.
- Das vorhandene Musicplayer-Widget wird direkt gerendert und behält Playlist, Transport, Seek, Lautstärke, Shuffle, Repeat, Upload und Import generierter Musik.
- Der tote Link `/musicplayer` wird in Phase B nicht mehr als Ersatz für den eingebetteten Player angeboten.
- Unterhalb der `xl`-Breite bleibt das bestehende Buddy-Verhalten unverändert; eine vollwertige responsive Player-Seite folgt in Phase C.

### Zuständigkeit und Lifecycle

- Phase B verwendet weiterhin den lokalen `useAudioPlayer`-State des Widgets.
- Wiedergabe endet beim Verlassen/Unmounten der Buddy-Seite.
- Es werden keine Backend-, Datenbank- oder Stream-Änderungen vorgenommen.

## Phase C: Audio-/Videoplayer-Modul

Das bestehende Modul wird unter Beibehaltung seiner Modul-ID und gespeicherten Tracks erweitert:

- eigene Cockpit-Route und Navigation,
- gemeinsame Audio-/Video-Bibliothek,
- zunächst browsernative Audio-/Videoformate ohne serverseitiges Transcoding,
- großer Player auf der Modulseite,
- kompakte Now-Playing-Steuerung im Buddy-Media-Slot,
- sichere Streaming-Authentifizierung ohne langlebiges JWT in der URL,
- definierte Multiuser-Sichtbarkeit und Besitzregeln,
- optional globaler Player-Lifecycle für unterbrechungsfreie Wiedergabe über Seitenwechsel.

Die Entscheidung über globale, seitenübergreifende Wiedergabe wird vor Phase C bestätigt.

## Sicherheitsgrenzen

- Kein harter Core-Import eines installierbaren Moduls.
- Phase B erweitert keine API und verändert keine Berechtigungen.
- Phase C validiert Endung, MIME und Dateisignatur, setzt Größenlimits und verwendet parametrisierte Datenbankzugriffe.
- Das vorhandene Query-JWT für `<audio src>` wird in Phase C durch authentifizierten Blob-Abruf oder kurzlebige, zweckgebundene Streamtickets ersetzt.
- Kein frei konfigurierbarer Remote-URL-Player im MVP.
- Kein ffmpeg-Transcoding im Requestpfad.

## Akzeptanzkriterien Phase B

- Mit installiertem Musicplayer erscheint im Buddy rechts ein funktionierender Musikplayer.
- Ohne Musicplayer baut und startet das Core-Frontend unverändert.
- Andere allgemeine `buddyWidgets` werden nicht automatisch in den Media-Slot gezogen.
- Die zehn vorhandenen Tracks bleiben unverändert abspielbar.
- Der Modulgenerator erzeugt den neuen optionalen Export deterministisch.
- TypeScript-Build, ESLint, Cockpit-Offline-Guard und relevante Modultests sind grün.
- Die Funktion wird im installierten System per Browser verifiziert.

## Nicht in Phase B

- Video-Upload oder Video-Wiedergabe,
- eigener Musicplayer-Tab,
- globale Wiedergabe über Route-Wechsel,
- neue Player-Persistenz,
- Stream-Auth-Umbau,
- Wiedereinführung aller früheren Buddy-Modulboxen.
