# Admin-Cockpit – die Übersicht über alles, was HydraHive verwaltet

Das Admin-Cockpit ist die Startseite für die Verwaltung von HydraHive. Es zeigt dir auf einen Blick, wo welche Einstellung liegt und ob der Server gesund ist. Es ist nur für Admins da.

## So startest du

1. Melde dich mit einem Admin-Konto an. Andere Konten sehen das Admin-Cockpit nicht. Wer die Seite trotzdem aufruft, landet wieder auf der Startseite.
2. Öffne **Admin** in der Navigation oder auf der Startseite im Bereich **Verwaltung**.
3. Du siehst drei Kästen: links **Verwaltung**, in der Mitte **Betriebszentrale** und rechts **Zustand**.
4. Klicke auf einen Eintrag. Das passende Fenster öffnet sich über der Startseite.
5. Schließe das Fenster mit dem X oben rechts. Du bist wieder auf der Übersicht.

## Was du damit machen kannst

### Verwaltung

Hier liegen die Bereiche, in denen du HydraHive einrichtest. Jeder Eintrag öffnet ein eigenes Fenster:

- **System**: Zustand, Netzwerk und Sicherung des Servers. Mehr dazu weiter unten und im Hilfe-Artikel „System“.
- **Benutzer**: Konten, Gruppen und API-Keys. Siehe Hilfe-Artikel „Benutzer“.
- **Freigaben**: Hier legst du fest, wer was nutzen darf. Siehe Hilfe-Artikel „Freigaben und Gruppen“.
- **Module**: Zusatzfunktionen installieren und aktualisieren. Mehr dazu unter „Updates“.
- **Extensions**: Gitea und Docker-Dienste. Siehe Hilfe-Artikel „Extensions“.
- **Plugins**: Werkzeuge für deine Agenten. Siehe Hilfe-Artikel „Plugins“.
- **Credentials**: Tokens und Schlüssel. Siehe Hilfe-Artikel „Credentials“.
- **Archiv**: Gelöschte Dinge, Freigabe und Speicherort auf einem NAS. Das Fenster heißt **Archiv & Sicherung**.

### Betriebszentrale

Hier steuerst du den laufenden Betrieb:

- **LLM**: Sprachmodelle und Anbieter. Siehe Hilfe-Artikel „LLM-Konfiguration“.
- **MCP**: MCP-Server. Siehe Hilfe-Artikel „MCP-Server“.
- **Skills**: Anleitungen für deine Agenten. Dieser Eintrag öffnet eine eigene Seite statt eines Fensters. Siehe Hilfe-Artikel „Skills“.
- **VMs** und **Container**: Virtuelle Maschinen und Linux-Container. Siehe die Hilfe-Artikel „Virtuelle Maschinen (VMs)“ und „Container“.
- **Compute-Nodes** und **Compute-Jobs**: Weitere Rechner und die Aufträge darauf. Siehe die gleichnamigen Hilfe-Artikel.
- **Automationen**: Öffnet das Fenster **Intervallaufgaben**. Dort siehst du Aufgaben, die regelmäßig laufen.
- **Föderation**: Verbindung zu anderen HydraHive-Servern. Siehe Hilfe-Artikel „Federation“.
- **Zahnfee**: Siehe Hilfe-Artikel „Zahnfee“.
- **Globale Einstellungen**: Öffnet das Fenster **Einstellungen**. Mehr dazu weiter unten.

### Zustand

Der rechte Kasten **Zustand** prüft den Server, sobald du die Seite öffnest. Probleme stehen ganz oben und sind rot. Bei einem Problem steht direkt darunter, was nicht stimmt.

| Prüfung | Was geprüft wird |
|---|---|
| **DB** | Die Datenbank lässt sich lesen und beschreiben. |
| **LLM** | Es gibt eine LLM-Einstellung mit Standard-Modell und mindestens einem Anbieter. |
| **Workspaces** | Der Arbeitsordner der Agenten ist da und beschreibbar. |
| **Disk** | Es sind mehr als 5 % Speicherplatz frei. |
| **System** | Offene Updates des Betriebssystems und ob der Rechner neu starten muss. Diese Prüfung gibt es nur auf Linux-Servern mit apt. |

Ein Klick auf eine Prüfung öffnet das Fenster **System** mit allen Einzelheiten. Der Knopf **Admin-Agent öffnen** bringt dich zum Buddy, wo du nach der Ursache fragen kannst.

Der Kasten prüft nur einmal beim Öffnen der Seite. Das Fenster **System** aktualisiert sich dagegen alle 10 Sekunden selbst.

### Das Fenster System

Das Fenster **System** hat diese Reiter:

- **Überblick**: Prüfungen, Zahlen zu Agenten, Projekten, Sessions, Nachrichten und Werkzeug-Aufrufen sowie die Version. Ein Punkt am Reiter zeigt eine fehlgeschlagene Prüfung.
- **Harness**: Eine Prüfung, wie gut die Agenten arbeiten. Sie liest nur und ändert nichts.
- **Netzwerk**: AgentLink, Tailscale, Netzwerk-Bridge und SMB-Freigaben.
- **Erweiterungen**: **Zusatz-Module** und lokale Bild- und Videoerzeugung.
- **Sicherung**: System-Backup und Umzug auf einen anderen Server.

Oben im Fenster findest du den Knopf **Einstellungen**. Mit **Service neu starten** startest du HydraHive neu. Der Server ist dann einige Sekunden lang nicht erreichbar. Einzelheiten stehen im Hilfe-Artikel „System“.

### Einstellungen

Das Fenster **Einstellungen** erreichst du über **Globale Einstellungen** oder über den Knopf **Einstellungen** im Fenster **System**. Für jede Gruppe gibt es einen Reiter, zum Beispiel **Websuche**, **Mail**, **Discord**, **AgentLink**, **Health**, **Krypto**, **Home Assistant**, **Hilfe**, **System**, **Agenten** und **Module**.

- Schalter speichern sofort. Ein Textfeld wird gespeichert, sobald du es verlässt und etwas geändert hast.
- Kennwörter und Schlüssel werden nie angezeigt. Ist einer gesetzt, steht im Feld **•••••••• (gesetzt)**.
- Das Schild **GUI** heißt: Dieser Wert wurde hier in der Oberfläche gesetzt.
- Ging das Speichern schief, erscheint **Fehler beim Speichern**. Der Reiter bekommt außerdem einen Punkt.
- Die SearXNG-URL gilt sofort. Mail, Discord und AgentLink brauchen erst einen Neustart.

Zwei Einstellungen lohnen einen eigenen Blick:

- **Projektarbeit nur mit Zieldokument** im Reiter **Agenten**: Ist der Schalter an, darf ein Agent einen Projekt-Agenten nur dann mit Bauen, Reparieren oder Umbauen beauftragen, wenn er ein Zieldokument mit Zielbild und Abnahme-Punkten mitgibt. Fragen und Prüfungen gehen immer. Ab Werk ist der Schalter aus.
- **Health-Daten gehören Nutzer** im Reiter **Health**: Hier trägst du den Benutzernamen ein, unter dem eingehende Gesundheitsdaten abgelegt werden. Ohne Eintrag nimmt der Server keine Gesundheitsdaten an.

### Updates

- HydraHive selbst: Unten in der Fußleiste steht die Version. Gibt es ein Update, erscheint dort ein Pfeil (↑). Ein Klick öffnet die Abfrage **Jetzt aktualisieren?**. Mit **Update starten** geht es los. Der Server startet dann neu und ist ein bis zwei Minuten nicht erreichbar. Nur Admins können den Pfeil anklicken.
- Erneut einspielen: Ist alles aktuell, zeigt die Fußleiste Admins stattdessen einen Knopf mit dem Hinweis **Update erzwingen / Rebuild**.
- Module und Plugins: Haben Module oder Plugins neue Versionen, zeigt die Fußleiste eine Zahl. Ein Klick öffnet das Fenster **Module** bzw. **Plugins**. Im Fenster **Module** gibt es die Reiter **Installiert** und **Verfügbar**, eine Suche und den Knopf **Alle updaten**. Jedes Modul kannst du auch einzeln über seinen eigenen Knopf auf den neuen Stand bringen.
- Betriebssystem: Offene Updates des Betriebssystems meldet die Prüfung **System** im Kasten **Zustand**. Sie kommen mit dem nächsten Update von HydraHive.
- Mit dem Schalter **Update-Check aktiv** im Reiter **System** der Einstellungen sucht HydraHive nicht mehr regelmäßig nach neuen Versionen. Der Schalter wirkt nach einem Neustart.

### Zusatz-Module

**Zusatz-Module** sind Teile, die nicht zum Kern gehören und die du nachträglich installieren kannst. Du findest sie im Fenster **System** im Reiter **Erweiterungen**. Das sind:

- **Container (incus)**
- **Virtuelle Maschinen (QEMU/KVM)**
- **Samba-Freigaben / Dateifreigabe**
- **WhatsApp-Bridge**
- **Voice (Sprache rein/raus)**
- **Tailscale**

Klicke auf **Installieren** und bestätige mit **Jetzt installieren**. Vorher siehst du, was dafür noch nötig ist und ob HydraHive dabei kurz neu startet. Das Protokoll läuft mit. Es kann immer nur eine Installation gleichzeitig laufen. Nicht verwechseln: Die Module im Fenster **Module** kommen aus dem Modul-Hub, die **Zusatz-Module** sind Teile des Servers selbst.

## Gut zu wissen

- Fenster schließen: Ein Fenster schließt nur über das X. Ein Klick daneben oder die Escape-Taste schließt es nicht. So gehen keine Eingaben verloren.
- Lesezeichen: Das offene Fenster und der Reiter stehen in der Adresszeile. Ein Lesezeichen oder Link öffnet genau dieses Fenster wieder. Alte Adressen, etwa für Benutzer, Module oder Einstellungen, führen automatisch zum passenden Fenster.
- Nicht-Admins und System: Wer kein Admin ist, sieht im Fenster **System** nur die Reiter **Überblick** und **Netzwerk**. Die Knöpfe **Einstellungen** und **Service neu starten** fehlen dann.
- Hinweis nach Updates: Sind nach einem Update Funktionen nur noch für Admins da, erscheint in der Mitte einmal der Hinweis **Neue Freigaben nach dem Update**. Mit **Freigaben öffnen** gibst du sie an Nutzer oder Gruppen frei. **Verstanden** blendet den Hinweis aus.

*Stand: HydraHive 2.0.0, 23.11.2026*
