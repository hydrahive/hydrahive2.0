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
- Das **Zahnrad** öffnet die Kontoeinstellungen.
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

Die geplanten Werkzeuge `mailbox_accounts`, `mailbox_search`, `mailbox_read`,
`mailbox_draft` und `mailbox_send` sind in dieser Version **noch nicht
verfügbar**. Die allgemeinen HydraHive-Werkzeuge `read_mail` und `send_mail`
verwenden die globale Mail-Konfiguration und sind nicht mit den Konten dieses
Mailbox-Moduls gleichzusetzen.

Projektfreigaben und Mailbox-Zugriff für Agenten folgen in einer späteren Etappe.
Agentenversand soll dann jede Mail vor dem Senden einzeln bestätigen lassen.

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
