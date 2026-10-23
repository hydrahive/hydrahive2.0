# Mailbox

## Was ist das?

**Mailbox** ist das Webmail und Mailarchiv von HydraHive. Du kannst mehrere
IMAP-/SMTP-Konten lesen und benutzen. Jede abgeglichene Mail wird zusätzlich als
`.eml` lokal archiviert. Wird eine Mail später auf dem Mailserver gelöscht,
bleibt die Archivkopie erhalten und ist unter **Nur im Archiv** auffindbar.

## Ein Konto hinzufügen

1. Öffne **Mailbox** und klicke links auf **Konto hinzufügen**.
2. Trage die Mailadresse ein. Mailbox schlägt bei bekannten Anbietern die
   Serverdaten vor.
3. Wähle die Anmeldeart:
   - **Passwort** für normale IMAP-/SMTP-Konten. Gmail benötigt üblicherweise ein
     App-Passwort statt des normalen Google-Passworts.
   - **Microsoft** für Outlook, Hotmail oder Microsoft 365. Folge dem angezeigten
     Geräte-Code. Falls Microsoft noch nicht eingerichtet ist, muss ein Admin
     zuerst die Microsoft-Anwendungs-ID hinterlegen.
4. Unter **Server-Einstellungen** kannst du Kontoname, Benutzername, IMAP- und
   SMTP-Server prüfen oder ändern.
5. Beim Speichern prüft Mailbox die Anmeldung. Danach werden alle Ordner und alle
   Jahre abgeglichen. Bei großen Konten kann der erste Abgleich lange dauern.

## Linke Ordnerleiste

- **Alle Posteingänge** sammelt die Posteingänge aller eingerichteten Konten.
- Die Ordner eines Kontos sind beim ersten Öffnen **eingeklappt**. Klicke auf den
  Kontonamen oder den Pfeil, um sie auf- oder wieder zuzuklappen.
- Mailbox merkt sich diesen Zustand in diesem Browser. Neu hinzugefügte Konten
  starten ebenfalls eingeklappt.
- Der runde Punkt zeigt den Kontostatus. Der Kreispfeil ruft das Konto sofort ab.
- Das **Zahnrad** öffnet die Kontoeinstellungen (Absender, Signatur,
  Freigaben für Agenten, Konto entfernen).
- **Entwürfe** enthält deine gespeicherten Entwürfe.
- **Nur im Archiv** zeigt Mails, die nicht mehr auf dem Server liegen.

## Absendername und Signatur festlegen

1. Klicke links neben dem gewünschten Konto auf das **Zahnrad**.
2. Trage unter **Absendername** den Namen ein, den Empfänger sehen sollen.
3. Hinterlege bei Bedarf eine **Signatur** und klicke auf **Speichern**.

Die Absenderadresse ist die Mailadresse des eingerichteten Kontos. Beim Schreiben
kannst du das Absenderkonto auswählen. Die Adresse wird nicht frei überschrieben;
der einstellbare Absendername und die Signatur gelten je Konto.

Im selben Dialog kannst du ein Konto entfernen. Dabei wird nur der Zugang
entfernt: Bereits archivierte Mails bleiben im lokalen Archiv und in der Suche.

## Mails lesen und suchen

- Klicke in der mittleren Liste auf eine Mail, um sie rechts zu öffnen.
- Externe Bilder werden aus Datenschutzgründen zunächst nicht geladen. Nutze
  **Bilder laden**, wenn du sie für diese Mail sehen möchtest.
- Anhänge kannst du unterhalb der Mail herunterladen.
- Das Suchfeld durchsucht alle archivierten Mails. Unterstützte Filter sind unter
  anderem `von:`, `an:`, `betreff:`, `hat:anhang`, `vor:`, `nach:`, `konto:` und
  `ordner:`.
- Mehrere Mails lassen sich auswählen und gemeinsam bearbeiten.

## Schreiben, antworten und Entwürfe

- **Neue Mail** öffnet das Schreibfenster.
- Im Feld **Von** wählst du das Konto, über das gesendet wird.
- Unterstützt werden **Antworten**, **Allen antworten**, **Weiterleiten**, Cc/Bcc
  und Anhänge.
- Entwürfe werden gespeichert und können links unter **Entwürfe** wieder geöffnet
  werden.
- Pro Konto gilt eine Versandgrenze. Ist sie erreicht, zeigt Mailbox einen Hinweis
  und sendet nicht weiter.

## Löschen und Archiv

**Löschen** verschiebt eine Mail normalerweise zuerst in den Papierkorb des
Mailservers. Löschst du sie dort erneut, wird sie endgültig vom Server entfernt.
Die lokale Archivkopie bleibt in beiden Fällen erhalten und erscheint danach
unter **Nur im Archiv**. Das Mailarchiv ist deshalb nicht dasselbe wie der
Papierkorb.

## Benachrichtigungen und Tastenkürzel

Die Glocke aktiviert Browser-Benachrichtigungen für neue Post. Der Browser fragt
dafür einmal nach Erlaubnis.

- `j` / `k`: nächste bzw. vorherige Mail
- `r`: antworten
- `a`: allen antworten
- `f`: weiterleiten
- `e`: archivieren
- `#`: löschen
- `/`: Suche fokussieren
- `c`: neue Mail

## Agenten und Mailbox

Agenten sehen ein Mailkonto **nur, wenn du es freigibst**. Ohne Freigabe finden
die Mailbox-Werkzeuge nichts.

### Konto für ein Projekt freigeben

1. Klicke links neben dem Konto auf das **Zahnrad**.
2. Unter **Freigaben für Agenten** wählst du ein Projekt (oder **Mein Buddy
   (ohne Projekt)**) und klickst auf **Freigeben**.
3. Wähle die **Stufe**:
   - **lesen**: suchen, Mails lesen und Anhänge in den Arbeitsordner holen
     (`mailbox-anhaenge/`).
   - **Entwurf**: zusätzlich Entwürfe anlegen, Mails verschieben und als
     gelesen/markiert setzen.

Die Stufe lässt sich später in der Liste der Freigaben umstellen.

Mit dem Mülleimer-Symbol nimmst du die Freigabe wieder zurück. Wird das Konto
entfernt, verschwinden auch seine Freigaben.

### Wer darf was?

- Freigeben kann nur der Besitzer des Kontos, und nur in Projekte, in denen er
  selbst Mitglied ist.
- Ein Agent sieht das Konto nur, wenn er für ein **Mitglied** dieses Projekts
  arbeitet. Andere Projekte sehen es nicht.
- **Mein Buddy** gilt nur für deinen eigenen Buddy ohne Projekt.
- Agenten können **nie senden und nie löschen**. Einen Entwurf prüfst und
  sendest du selbst im Webmail. Versand mit Bestätigung folgt in einer
  späteren Version.
- Ein Agent ändert nur Entwürfe, die ein Agent in **diesem** Projekt angelegt
  hat. Deine eigenen Entwürfe fasst er nicht an.

### Die Werkzeuge

| Werkzeug | Wofür |
|---|---|
| `mailbox_accounts` | freigegebene Konten und ihre Ordner |
| `mailbox_search` | suchen, mit denselben Filtern wie im Suchfeld (höchstens 50 Treffer) |
| `mailbox_read` | eine Mail als Text lesen, mit Liste der Anhänge |
| `mailbox_attachment` | einen Anhang in den Arbeitsordner speichern (bis 25 MB, nie überschreiben) |
| `mailbox_draft` | Stufe Entwurf: Entwurf anlegen oder eigenen ändern, auch als Antwort/Weiterleitung |
| `mailbox_move` | Stufe Entwurf: Mails in einen anderen Ordner verschieben |
| `mailbox_flag` | Stufe Entwurf: gelesen/ungelesen, markieren/Markierung entfernen |

### Entwürfe vom Agenten

Entwürfe eines Agenten erscheinen bei dir unter **Entwürfe** mit dem Kennzeichen
**Agent**. Öffne sie, prüfe Empfänger und Text, und sende sie erst dann selbst.

Mailtext ist **fremder Text**: Der Agent bekommt ihn ausdrücklich als Fremdinhalt
markiert und soll darin enthaltene Anweisungen nie befolgen. Zugangsdaten und
Passwörter sieht ein Agent nie.

Jeder Zugriff steht im **Protokoll** (wer, wann, welches Werkzeug, Ergebnis –
ohne Mailinhalt). Die letzten Zugriffe siehst du im Kontodialog unter
**Letzte Agenten-Zugriffe**.

Die allgemeinen Werkzeuge `read_mail` und `send_mail` nutzen weiterhin die
globale Mail-Konfiguration und haben mit diesen Konten nichts zu tun.

## Typische Probleme

- **Konto bleibt leer:** Der erste Abgleich kann noch laufen. Prüfe den Fortschritt
  unter dem Kontonamen oder klicke auf den Kreispfeil.
- **Anmeldung abgelehnt:** Prüfe Benutzername, App-Passwort und Serverdaten. Bei
  Microsoft-Konten kannst du die Anmeldung im Kontodialog erneuern.
- **Gesendete Mail fehlt im Ordner:** Der Versand kann erfolgreich sein, obwohl der
  Anbieter die Gesendet-Kopie verzögert ablegt. Die lokale Archivkopie bleibt
  erhalten.
- **Ordner klappt nach Neuladen wieder zu:** Der Browser darf den lokalen Speicher
  nicht blockieren oder beim Schließen löschen.
