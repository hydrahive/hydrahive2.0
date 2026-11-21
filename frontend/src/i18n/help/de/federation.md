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
  gesendet werden (Standard: keiner) und welche Projekte nie gesendet werden.
  Der eigentliche Versand kommt in einer späteren Ausbaustufe; bis dahin werden nur
  die Einstellungen gespeichert.
