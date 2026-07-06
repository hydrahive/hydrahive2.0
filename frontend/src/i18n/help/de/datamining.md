# Datamining — durchsuchen, was deine Agenten getan haben

## Was ist das?

Datamining ist dein **Archiv und deine Lupe** für alles, was in HydraHive
passiert ist: jede Konversation, jeder Werkzeug-Aufruf, jede Sitzung. Du kannst
darin suchen, Verläufe nachvollziehen und auswerten, wie viel „gearbeitet" (und
verbraucht) wurde.

Kurz: Der normale Chat zeigt dir das *Jetzt* — Datamining zeigt dir die *gesamte
Vergangenheit* durchsuchbar.

## Die Reiter

### Live-Feed
Ein Live-Strom der aktuellen Ereignisse — du siehst quasi in Echtzeit, was die
Agenten gerade tun (Nachrichten, Werkzeug-Aufrufe). Gut, um im Betrieb
mitzuschauen.

### Suche
Volltextsuche über **alle** Konversationen. Du kannst:
- nach einem **Suchbegriff** filtern,
- nach **Ereignis-Typ** einschränken (z.B. nur Nutzer-Eingaben, nur
  Werkzeug-Aufrufe),
- die **semantische Suche** einschalten — dann wird nicht nur nach exakten Wörtern
  gesucht, sondern nach **inhaltlicher Ähnlichkeit** (findet Passendes auch, wenn
  andere Wörter benutzt wurden).

### Sessions
Die Liste aller vergangenen **Sitzungen** mit Datum, Agent und Benutzer. Ein Klick
öffnet die Detailansicht mit allen **Events** der Sitzung — praktisch, um einen
kompletten Verlauf Schritt für Schritt nachzulesen.

### Token-Statistik
Auswertung des **Verbrauchs**: erstellt/zuletzt aktiv, Anzahl Nachrichten und
Token-Kennzahlen. Hier siehst du, welche Sitzungen besonders „teuer" waren.

### Graph
Eine visuelle Darstellung der Zusammenhänge (z.B. Sitzungen und die beteiligten
Benutzer). Über **Graph laden** wird die Ansicht aufgebaut.

## Import

Über die **Importieren**-Funktion lassen sich zusätzliche Datenquellen ins Archiv
holen (z.B. aus Extensions/Issues). Ist ein Import konfiguriert, siehst du den
Status **Mirror aktiv**.

## Schritt-für-Schritt: etwas Vergangenes finden

1. Reiter **Suche** öffnen.
2. Suchbegriff eingeben — bei ungenauer Erinnerung die **semantische Suche**
   einschalten.
3. Optional den **Ereignis-Typ** einschränken.
4. Treffer anklicken → im Reiter **Sessions** die zugehörige Sitzung im Detail
   ansehen.

## Typische Fragen

- **„Wann haben wir über X gesprochen?"** → Suche (ggf. semantisch), dann Session
  öffnen.
- **„Welche Sitzung war so teuer?"** → Reiter **Token-Statistik**.
- **„Was macht der Agent gerade?"** → **Live-Feed**.
- **„Mirror inaktiv / nicht konfiguriert"** → Der Datenbank-Spiegel
  (`HH_PG_MIRROR_DSN`) ist nicht eingerichtet; das ist eine System-Einstellung.

## Tipps

- **Semantische Suche** ist dein Freund, wenn du dich nur ungefähr erinnerst.
- **Ereignis-Typ-Filter** grenzt Rauschen aus — z.B. nur „Nutzer-Eingaben", um
  schnell den Gesprächsfaden zu finden.
- **Token-Statistik regelmäßig prüfen**, wenn du Kosten im Blick behalten willst.
