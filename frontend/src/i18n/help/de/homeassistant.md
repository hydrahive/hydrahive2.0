# Home Assistant

## Was ist das?

Dieses Modul bindet dein **Home Assistant Smart Home** an HydraHive an: Du siehst
deine **Geräte** (Lampen, Schalter, Sensoren, Thermostate …) und kannst sie
**direkt schalten** — ohne die Home-Assistant-App zu öffnen. Auch dein Agent kann
darüber Geräte steuern.

## Was kann ich hier tun?

- **Geräte sehen**: alle Entities mit ihrem aktuellen Zustand.
- **Schalten**: Lampen an/aus, Schalter umlegen, Szenen auslösen usw.
- **Suchen**: über das Suchfeld nach Name oder `entity_id` filtern.
- **Favoriten**: häufig genutzte Geräte markieren und per **Nur Favoriten**
  einblenden.
- **Aktualisieren**: den aktuellen Zustand neu laden.

## Voraussetzung

Es muss eine **Verbindung zu deinem Home-Assistant-Server** eingerichtet sein
(Adresse + Zugangs-Token). Ohne diese Anbindung erscheinen keine Geräte. Die
Verbindung wird in den System-/Verbindungseinstellungen hinterlegt.

## Typische Fragen

- **„Keine passenden Geräte gefunden"** — Entweder ist die Anbindung nicht
  eingerichtet, oder der Suchbegriff passt auf kein Gerät. Suchfeld leeren und
  **Aktualisieren**.
- **„Schalten reagiert nicht"** — Prüfe, ob Home Assistant erreichbar ist und die
  Entity wirklich schaltbar ist (Sensoren zeigen nur an, sie schalten nicht).

## Tipps

- **Favoriten setzen** für die Geräte, die du täglich brauchst — spart das Suchen.
- **entity_id merken**: Über die genaue `entity_id` findest du ein Gerät am
  schnellsten (auch wenn der Anzeigename mehrdeutig ist).
