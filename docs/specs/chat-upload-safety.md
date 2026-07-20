# Chat-Dateiupload: sichtbare Limits und sicheres Streaming

## Was

Der Chat akzeptiert bis zu fünf Anhänge. Pro Datei gelten maximal **100 MiB**, pro Nachricht insgesamt maximal **200 MiB**. Bilder bis 5 MiB und Textdateien bis 100 KiB werden wie bisher als LLM-Inhalt verarbeitet; größere oder binäre Dateien werden blockweise in den aktiven Workspace geschrieben und dem Agenten über ihren Pfad angekündigt.

## Warum

Der bisherige Client verwirft Nicht-Bild-Dateien über 51.200.000 Bytes (ca. 48,8 MiB) ohne Rückmeldung. Eine knapp 54 MB große APK erscheint deshalb nicht als Anhang und nur der Nachrichtentext wird gesendet. Gleichzeitig liest das Backend Binärdateien vollständig in den RAM und speichert Projekt-Anhänge im generischen Agent-Workspace statt im aktiven Projekt-Workspace.

## Verhalten

### Grenzen

- maximal 5 Dateien pro Nachricht
- maximal 100 MiB pro Datei (`100 * 1024 * 1024` Bytes)
- maximal 200 MiB über alle Anhänge einer Nachricht (`200 * 1024 * 1024` Bytes)
- Bilder werden nur bis 5 MiB als Base64-Bildblock an das LLM gegeben
- erkannte Textdateien werden nur bis 100 KiB in den Prompt eingebettet
- größere Bilder, größere Textdateien und Binärdateien innerhalb der allgemeinen Grenzen werden als Dateien gespeichert

### Frontend

- APK, EXE und andere Binärdateien sind auswählbar; es gibt keine Dateiendungs-Whitelist.
- Abgelehnte Dateien verschwinden nicht still.
- Bei zu großer Einzeldatei, überschrittenem Gesamtlimit oder mehr als fünf Dateien erscheint eine lokalisierte Fehlermeldung.
- Akzeptierte Dateien erscheinen weiterhin als Dateichip.
- Wird nach einer Ablehnung eine gültige Datei gewählt, kann sie normal angehängt werden.

### Backend

- Das Backend erzwingt dieselben Einzel- und Gesamtgrenzen unabhängig vom Client.
- Binärdateien werden in festen Chunks geschrieben; es wird keine 100-MiB-Datei vollständig in einen Python-Bytestring geladen.
- Nginx und eine ASGI-Middleware begrenzen Chat-Message-Requests inklusive Multipart-Overhead auf 205 MiB, bevor FastAPI den Multipart-Body parst.
- Bei Überschreitung wird HTTP 413 mit strukturiertem, im Chat lokalisiertem Fehlercode geliefert.
- Uploads landen in einem eindeutigen Batch-Ordner unter `.hydrahive/uploads/`; bestehende Projektdateien werden niemals überschrieben.
- Mehrere gleichnamige Anhänge erhalten eindeutige Zieldateinamen.
- Unvollständige temporäre Dateien und der gesamte Batch werden bei Fehlern entfernt.
- Anhänge akzeptieren nur einen reinen Basis-Dateinamen; Pfadbestandteile, `.` und `..` werden abgelehnt.
- Bei einer Session mit gültiger `project_id` liegt der Batch im Projekt-Workspace; sonst im Agent-Workspace.
- Uploadvalidierung erfolgt bei Resend vor dem Löschen der bisherigen History.
- Hochgeladene APK/EXE werden nur gespeichert und niemals ausgeführt.

## Akzeptanzkriterien

- Eine Datei mit knapp 54 MB wird im Chat akzeptiert und im aktiven Projekt-Workspace gespeichert.
- Eine Datei über 100 MiB wird im Frontend sichtbar abgelehnt und serverseitig mit HTTP 413 abgewehrt.
- Mehrere Dateien über insgesamt 200 MiB werden sichtbar bzw. serverseitig abgelehnt.
- Dateien mit `../` im Namen können den Workspace nicht verlassen.
- Binär-Upload verwendet Chunk-Schreiben und hinterlässt bei Abbruch weder Teil-Datei noch verwaisten Batch.
- Bestehende Projektdateien bleiben auch bei gleichnamigem Upload unverändert.
- Mehrere gleichnamige Anhänge bleiben als getrennte Dateien erhalten.
- Projekt-Session und projektlose Session speichern in ihrem jeweils korrekten Workspace.
- Ein fehlgeschlagener Resend lässt die bisherige History unverändert.
- Bestehender Bild- und Textupload bleibt funktionsfähig.
- Frontend-Typecheck, ESLint und relevante Pytests sind grün.

## Nicht enthalten

- Uploads größer als 100 MiB pro Datei
- ISO-/VM-Disk-Uploads; dafür bleiben die spezialisierten Uploadwege zuständig
- Ausführung oder Installation hochgeladener Programme
- automatische Übermittlung von Dateien an externe Malware-Scanner
- Fortschrittsanzeige auf Byte-Ebene
