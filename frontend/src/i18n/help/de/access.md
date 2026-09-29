# Freigaben und Gruppen

## Was ist das?

Mit **Freigaben** legst du fest, **wer welche Funktion nutzen darf**. Mit
**Gruppen** fasst du Nutzer zusammen, zum Beispiel „Familie“ oder „Dev-Team“.
Eine Freigabe an eine Gruppe gilt für alle ihre Mitglieder.

Freigaben verwalten nur **Admins**. Admins selbst dürfen immer alles.

## Welche Funktionen sind geschützt?

Nur Funktionen, die ausdrücklich als „geschützt“ angemeldet sind. Alles andere
bleibt für alle Nutzer offen. Nach dem Update sind diese Funktionen **nur für
Admins**, bis du sie freigibst:

- **VMs** und **Container**
- **Föderation** (Workstations fernsteuern)
- **Home Assistant: Geräte schalten** (Ansehen bleibt für alle offen)
- **Voice**, **Archiver**, **OpenTor**

Ein Hinweis im Admin-Cockpit erinnert einmalig daran.

## Schritt-für-Schritt

### Gruppe anlegen
1. **Admin → Benutzer** öffnen.
2. Im Bereich **Gruppen** einen Namen eingeben und **Anlegen** klicken.
3. Mitglieder über **Mitglied hinzufügen** auswählen.

### Funktion freigeben
1. **Admin → Freigaben** öffnen.
2. In der Tabelle ist jede Zeile eine Funktion. Die Spalten sind **Alle**, deine
   Gruppen und einzelne Nutzer.
3. Ein Klick auf eine Zelle schaltet zwischen **–**, **benutzen** und
   **verwalten**.

Die Änderung wirkt sofort, ohne Neustart.

## Gut zu wissen

- **Agenten erben die Rechte ihres Besitzers.** Darf ein Nutzer keine Geräte
  schalten, bekommt auch sein Buddy das Werkzeug nicht. Im Agent-Editor sind
  solche Werkzeuge ausgegraut.
- Ohne Freigabe verschwindet der Menüpunkt. Wer die Adresse direkt aufruft,
  sieht „Kein Zugriff“.
- Wird eine Gruppe gelöscht, verschwinden auch ihre Freigaben. Wird ein Nutzer
  gelöscht, verschwinden seine Mitgliedschaften und Freigaben.
- Jede Änderung wird protokolliert.
- Unter **Profil → Meine Freigaben** sieht jeder Nutzer, was er darf.
