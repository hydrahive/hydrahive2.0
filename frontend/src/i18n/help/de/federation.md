# Federation

## Was ist das?

**Federation** verbindet deine HydraHive-Instanz mit **anderen Agent-Systemen
(Workstations)** über das **A2A-Protokoll** (Agent-to-Agent). So kann dein Agent
Aufgaben an entfernte, ferngesteuerte Agent-Systeme übergeben — z.B. an einen
Spezialisten auf einer anderen Maschine.

## Kernbegriffe

- **Workstation** — ein anderes, A2A-kompatibles Agent-System, das du hier
  registrierst.
- **Token** — das **Zugangsgeheimnis** der Ziel-Workstation. Ohne gültigen Token
  keine Verbindung.
- **TLS** — ob die Verbindung verschlüsselt läuft.

## Schritt-für-Schritt

1. **Hinzufügen** → **Workstation hinzufügen**.
2. Adresse und den **Token** der Ziel-Workstation eintragen (der Token stammt von
   der Gegenstelle).
3. Speichern — registrierte Workstations erscheinen in der Liste mit Status
   („Token konfiguriert" / „Kein Token", TLS an/aus).

## Typische Fragen

- **„Noch keine Workstations registriert"** — Normal am Anfang; mit **Erste
  Workstation hinzufügen** starten.
- **„Kein Token"** — Die Workstation hat kein gültiges Zugangsgeheimnis; ohne das
  klappt die Verbindung nicht.

## Tipps

- **Token sicher behandeln**: Er ist das Zugangsgeheimnis zur Gegenstelle — wie ein
  Passwort.
- **TLS bevorzugen**, wenn die Verbindung über ein Netzwerk läuft, das nicht
  vollständig vertrauenswürdig ist.

## Föderations-Katalog (Reiter „Server“)

Ideen und Tasks mehrerer Server an einer Stelle sehen. Ein Server ist der **Hub**,
die anderen schicken ihm ihre Einträge (nur Metadaten, der Volltext wird später live
nachgeladen).

- **Als Hub verwenden** — auf dem Client beim Partner einschalten, der Hub sein soll.
  Es gibt höchstens einen Hub, und die Kopplung muss aktiv sein.
- **Katalog annehmen** — auf dem Hub bei jedem Client einschalten, dessen Katalog
  angenommen werden soll.
- Ein Server ist entweder Hub für andere **oder** schickt selbst an einen Hub, nicht
  beides. Sonst erscheint eine Meldung, welcher Schalter zuerst aus muss.
- **Katalog-Sync** — Sync an/aus, Intervall (60–3600 Sekunden), welche Nutzer
  gesendet werden (Standard: keiner) und welche Projekte nie gesendet werden. Der
  Versand läuft alle paar Minuten automatisch und sofort bei Änderungen an einem
  gesendeten Eintrag.

## Gemeinsame Taskpflege

Ergänzt den Föderations-Katalog: Die eigenen Ideen und Tasks werden mit den anderen
gekoppelten Instanzen geteilt, und deren Einträge erscheinen hier zum Lesen. Geteilt
werden **nur Metadaten** (Titel, Status, Projekt, …) — der Volltext bleibt immer bei
der Instanz, auf der der Eintrag angelegt wurde, und wird bei Bedarf live
nachgeladen. Sichtbar sind Einträge nur unter demselben Nutzernamen: `till` auf
dieser Instanz sieht nur Einträge von `till` auf anderen Instanzen, sonst niemand.

Im Abschnitt „Katalog-Sync“ gibt es dafür zwei Schalter:

- **„Gemeinsame Taskpflege“** — teilt die eigenen synchronisierten Einträge mit den
  anderen Instanzen **und** zeigt deren Einträge hier an. Beides hängt an einem
  Schalter; es gibt kein getrenntes Nur-Anzeigen oder Nur-Teilen.
- **„Bearbeiten durch andere Instanzen erlauben“** — lässt sich erst einschalten,
  wenn „Gemeinsame Taskpflege“ an ist. Mit „Gemeinsame Taskpflege“ allein sind die
  eigenen Einträge anderswo nur **sichtbar**, nicht änderbar. Der Schalter wirkt erst
  ab der Etappe Bearbeiten — bis dahin ändert er noch nichts.

## Reiter „Katalog“

Zeigt die Kopie der Einträge anderer Instanzen, **nur lesen**. Spalten: Art
(Task/Idee), Kurz-ID, Titel, Status, Projekt, Instanz, geändert am. Filter nach
Instanz, Projekt, Status und Art, dazu eine Suche. Ohne eingeschaltete „Gemeinsame
Taskpflege“ oder ohne gesetzten Hub bleibt die Liste leer.
