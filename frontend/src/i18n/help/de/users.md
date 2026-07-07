# Benutzer

## Was ist das?

Hier verwaltest du, **wer sich bei HydraHive anmelden darf** — die Benutzerkonten
und ihre Rollen. Diesen Bereich sehen nur **Admins**. Zusätzlich verwaltest du
hier **API-Keys**: langlebige Tokens, mit denen externe Programme (z.B. ein
Skript oder ein MCP-Client) auf HydraHive zugreifen können, ohne sich per
Benutzername/Passwort einzuloggen.

## Die zwei Rollen

- **Admin** — darf alles: Benutzer anlegen/bearbeiten/löschen, System-
  Einstellungen, Module, VMs/Container usw.
- **Benutzer** — normaler Zugang zum Arbeiten (Chat, Projekte, …), aber ohne
  Verwaltungs- und System-Rechte.

## Schritt-für-Schritt

### Benutzer anlegen
1. **Neuer Benutzer** klicken.
2. **Benutzername** vergeben (nur Buchstaben, Ziffern, `_` und `-`), z.B. `alice`.
3. **Passwort** setzen.
4. **Rolle** wählen (Admin oder Benutzer).
5. Anlegen — der Benutzer kann sich jetzt anmelden.

### Passwort ändern
Beim Benutzer **Passwort ändern** wählen und ein neues vergeben. (Als Admin kannst
du das auch für andere tun.)

### Benutzer bearbeiten / löschen
Über die Aktionen am jeweiligen Eintrag. **Dich selbst kannst du nicht löschen** —
das verhindert, dass sich der letzte Admin aussperrt.

## API-Keys

Ein **API-Key** ist ein langlebiges Token für **maschinellen Zugriff** — z.B.
damit ein lokales Tool oder Skript die HydraHive-API nutzt, ohne interaktives
Login.

1. Einen Namen vergeben (z.B. `claude-code-local`) → **Key erzeugen**.
2. **Wichtig:** Der Key wird **nur einmal** angezeigt — sofort kopieren und sicher
   speichern. Danach ist er nicht mehr einsehbar.
3. Nicht mehr benötigte Keys **widerrufen** (löschen) — dann funktioniert das
   Token sofort nicht mehr.

## Typische Fehler

- **„Benutzername existiert bereits"** — Name schon vergeben, einen anderen wählen.
- **„Du kannst dich nicht selbst löschen"** — Absicht; lösche dich über einen
  zweiten Admin-Account, falls wirklich nötig.
- **API-Key verloren** — Nicht wiederherstellbar; einen neuen erzeugen und den
  alten widerrufen.

## Unterschied: Benutzer-Login vs. API-Key vs. Credentials

- **Benutzer** — Menschen, die sich im Browser anmelden.
- **API-Key** — Programme, die HydraHive **von außen** ansprechen (kein Login).
- **Credentials** (eigener Bereich) — Zugänge, die HydraHive-Agenten **nach außen**
  brauchen (z.B. ein Token für eine fremde Webseite). Nicht verwechseln.

## Tipps

- **Sparsam mit Admin-Rechten**: Nur wer wirklich verwalten muss, braucht Admin.
- **Ein API-Key pro Zweck/Tool** — so kannst du einzelne widerrufen, ohne andere
  zu treffen.
- **Starke Passwörter** vergeben, besonders für Admin-Konten.
