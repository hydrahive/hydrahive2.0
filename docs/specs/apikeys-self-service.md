# API-Keys: selbst verwalten, aber nur mit Login-Sitzung

Task 9e9439ff. Freigabe Till am 30.09.2026.

## Befund (30.09.2026)

- Die API erlaubt jedem Nutzer, eigene Keys anzulegen, zu sehen und zu löschen (sauber auf
  den Aufrufer begrenzt). Die Oberfläche dafür gab es aber nur im Admin-Cockpit.
  Normale Nutzer konnten Funktionen, die einen persönlichen Key brauchen (z. B. Skill
  medical-akte über ein Credential-Profil), nicht einrichten.
- **Sicherheitsbefund:** Ein API-Key konnte selbst weitere API-Keys anlegen (live getestet:
  201). Keys laufen nicht ab. Ein abgegriffener Key hätte sich dauerhafte Ersatz-Keys
  erzeugen können, auch ein Agent über ein Credential-Profil (fetch_url setzt den Key ein
  und bekommt die Antwort mit dem neuen Key im Klartext zurück).

## Änderung

- Neue Abhängigkeit `require_session_principal`: wie `require_principal`, lehnt aber
  API-Keys (`hhk_…`) mit **403 `session_required`** ab.
- `POST /api/auth/apikeys` und `DELETE /api/auth/apikeys/{id}` verlangen eine Login-Sitzung.
- `GET /api/auth/apikeys` bleibt mit Key möglich (nur Lesen, ohne Werte).
  Neu `?mine=true`: auch Admins bekommen nur die eigenen Keys.
- Profilseite: Bereich „Meine API-Keys“ (dieselbe Komponente wie im Admin-Cockpit,
  Modus `own`: nur eigene Keys, ohne Besitzer-Spalte, eigener Text).
- Bestehende Keys funktionieren unverändert für alle anderen Aufrufe.

## Sicherheit (Checkliste)

- Kein neuer Weg zu fremden Keys: Liste und Löschen bleiben auf den Nutzer begrenzt,
  Admin sieht alle nur ohne `mine`.
- Klartext-Key nur einmal in der Antwort auf POST, Liste ohne Wert und ohne Hash.
- Kein Aufrufer im Code, der Keys mit einem Key anlegt (geprüft: nur das Frontend mit Sitzung).
