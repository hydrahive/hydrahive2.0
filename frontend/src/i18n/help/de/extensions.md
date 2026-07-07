# Extensions

## Was ist das?

**Extensions** sind **externe Zusatzdienste**, die HydraHive um größere Fähigkeiten
erweitern — z.B. ein Matrix-Server für den Teamchat oder andere Integrationen. Sie
laufen als eigener Dienst, entweder **nativ** auf dem Server oder in **Docker**.

## Was kann ich hier tun?

- Verfügbare Extensions nach **Kategorie** durchsehen (installiert / nicht
  installiert).
- Eine Extension **installieren**, **deinstallieren** oder (falls sie eine
  Oberfläche hat) **öffnen**.
- Den **Status** sehen: Nicht installiert / Aktiv / läuft-aber-nicht-erreichbar.

## Nativ vs. Docker

- **Nativ** — der Dienst läuft direkt auf dem Server.
- **Docker** — der Dienst läuft in einem Container. Dafür muss **Docker verfügbar**
  sein (die Seite zeigt an, ob Docker installiert ist).

## Schritt-für-Schritt

1. Eine Extension auswählen.
2. **Installieren** (bei Docker-Extensions muss Docker vorhanden sein).
3. Nach der Installation zeigt der Status **Aktiv**; hat die Extension eine
   Oberfläche, kannst du sie **Öffnen**.

## Typische Fragen

- **„Docker ist nicht installiert"** — Für Docker-basierte Extensions muss zuerst
  Docker auf dem Server eingerichtet werden.
- **„läuft, aber nicht erreichbar"** — Der Dienst startet, ist aber (noch) nicht
  ansprechbar; kurz warten oder das Extension-Log prüfen.

## Abgrenzung

- **Extension** — externer **Dienst/Integration** (nativ oder Docker).
- **Plugin** — Agenten-**Werkzeuge** im Hintergrund.
- **Modul** — eine **Seite/Feature** in HydraHive.

## Tipps

- **Nur bei Bedarf installieren** — jeder laufende Dienst braucht Ressourcen.
