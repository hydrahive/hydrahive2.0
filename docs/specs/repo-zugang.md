# Spec: Zugang zum Code über GitHub-Freischaltung (privates Repo)

Stand 14.10.2026 · von Till gewünscht. Freigegeben: **über Discord gibt es nur Lesezugriff, Schreibrecht vergibt nur Till von Hand.**

## Was

Der HydraHive-Code liegt künftig in einem **privaten** GitHub-Repo. Updates bekommt nur, wer freigeschaltet ist:

1. Der Nutzer meldet sich auf dem HydraHive-Discord an und bittet Buddy um Freischaltung, mit seinem GitHub-Namen.
2. Buddy gibt diesen GitHub-Nutzer im Repo mit der Rolle **Read** frei. GitHub schickt eine Einladung.
3. Der Nutzer trägt in **Admin → System → Zugang zum Code** seinen GitHub-Token ein und drückt „Zugang testen“.
4. Ab dann laufen Updates, die Anzeige „Update verfügbar“ und Neuinstallationen über diesen Token.

## Warum

Code wird kopiert, der Copyright-Hinweis entfernt, Mitarbeit kommt keine zurück. Ein privates Repo mit Freischaltung gibt halbwegs Kontrolle: Man weiß, wer Zugang hat, und kann ihn wieder entziehen. Vollständig verhindert ist Kopieren damit nicht. Wer lesen darf, kann den Code weiterhin kopieren.

## Fakten (geprüft 14.10., GitHub-Doku)

- In einem privaten Repo eines **persönlichen Kontos** gibt es nur Schreibrecht, kein Nur-Lesen („Collaborators can't have read-only access to repositories owned by a personal account“). → Das Repo muss in eine **Organisation**. Die ist kostenlos und hat die Rolle `Read`.
- Externe Mitwirkende an Repos einer Organisation brauchen einen **klassischen Token** (`repo`-Recht). Fein einstellbare Tokens gehen für sie nicht.
- GitHub Free für private Repos: 2.000 Actions-Minuten im Monat. Eigene Runner sind kostenlos. Geschützte Branches erst ab Team.
- Beim Verschieben eines Repos leitet GitHub alte URLs weiter. Klone und `git pull` funktionieren weiter.

## Grundregel (Till)

Viele Nutzer kennen wir nicht, auf deren Server haben wir keinen Zugriff. Daher:
- Alles läuft über die Admin-Konsole, ohne Terminal, ohne Bearbeiten von `install.conf` oder env von Hand.
- UI-Texte nennen weder Terminal noch Dateien.
- **Die Umstellung darf keinen Server stranden lassen**, deshalb gibt es feste Etappen. Das Repo wird erst privat, wenn die Zugangs-Funktion auf allen aktiven Servern angekommen ist.

## Wie (grob)

### Etappe 1: Zugang zum Code in der Admin-Konsole (Repo bleibt öffentlich)

- **Einstellung `config_dir/code-access.json`:** GitHub-Benutzername und Token, verschlüsselt mit `credentials/_crypto` wie beim Archiv-NAS (`remote_config.py`). Die Datei gehört dem Dienstnutzer und wird vom Backend gepflegt, der Installer schreibt sie nie neu. Nach außen erscheint der Token nie, nur `token_set`.
- **„Zugang testen“:** `git ls-remote <repo> refs/heads/main` mit dem Token, dazu eine GitHub-API-Abfrage `GET /repos/<repo>`, um die Rolle zu lesen. Mögliche Ergebnisse: „ok, Rolle Read/Write“, „Token ungültig“, „noch nicht freigeschaltet oder Einladung nicht angenommen“, „GitHub nicht erreichbar“.
- **Token weitergeben, ohne ihn zu speichern:**
  - Nie in die Remote-URL, nie in `.git/config`, nie auf die Kommandozeile (dort wäre er in `ps` sichtbar).
  - Stattdessen über einen kleinen `GIT_ASKPASS`-Helfer, der den Token aus einer Umgebungsvariable des Prozesses liest.
  - Das gilt für drei Stellen: den Update-Check (`api/version.py`), `update.sh` und die Hub-Clients für Module, Plugins und Themes, falls diese Repos später auch privat werden.
- **`update.sh`:**
  - Läuft als root über systemd und holt den Code mit `git pull` als Nutzer `hydrahive`.
  - Ist ein Token eingetragen, nutzt der Pull ihn über einen kleinen Python-Helfer im venv. Der entschlüsselt den Token für genau diesen einen Aufruf.
  - Ohne Token bleibt alles wie heute.
  - Scheitert der Pull mit „nicht berechtigt“, erscheint im Update-Fenster eine klare Meldung: „Zugang zum Code fehlt. Admin → System → Zugang zum Code“.
- **Footer und Dashboard:** Kann der Update-Check das Repo nicht lesen, zeigt die Konsole „Zugang zum Code fehlt“ statt still „aktuell“.

### Etappe 2: Freischaltung über Discord durch Buddy

- **Neues Werkzeug `github_repo_access`**, nur für Buddy:
  - Aktionen: `invite` (immer Rolle `read`, fest im Code), `list` und `remove`.
  - Repo, Organisation und Admin-Token kommen aus dem Credential-Store des Admins.
  - Ein anderer Wert für die Rolle ist nicht möglich. Das Werkzeug kennt kein `write`.
- **Wer darf freischalten lassen:** Jedes Mitglied des HydraHive-Discords darf fragen, auch per Direktnachricht. Buddy prüft vor der Freischaltung:
  - Gibt es den GitHub-Nutzer, und ist das Konto älter als X Tage? X ist eine Einstellung, Standard 30.
  - Hat dieser Discord-Account schon einen anderen GitHub-Namen freigeschaltet? Höchstens einer pro Discord-Account.
- **Liste der Freischaltungen:** Pro Eintrag Discord-ID, Discord-Name, GitHub-Name, Datum und ob die Einladung angenommen wurde. Admin → System → Zugang zum Code → „Freigeschaltete Nutzer“. Dort kann der Admin Einträge auch entfernen, das entfernt ihn zugleich im Repo.
- **Rauswerfen:**
  - Buddy (auf Anweisung von Till im Discord) oder der Admin entfernt den Nutzer.
  - Der Nutzer verliert den Lesezugriff. Weitere Updates bekommt er nicht mehr.
  - Seine schon installierte Version läuft weiter.
- **Schreibrecht:** gibt es nicht über Buddy, die Admin-Konsole oder ein anderes Werkzeug. Till vergibt es nur direkt in GitHub.

### Etappe 3: Umzug und Umstellung (Till, mit Begleitung)

1. Organisation anlegen, zum Beispiel `hydrahive-org`, und das Repo `hydrahive/hydrahive2.0` dorthin übertragen. Die alten URLs werden weitergeleitet.
2. Branch-Schutz prüfen: In einer kostenlosen Organisation gibt es ihn bei privaten Repos nicht. Weil nur Till Schreibrecht hat, ist das akzeptabel.
3. CI: entweder mit den 2.000 Minuten im Monat auskommen oder einen eigenen Runner auf Tills Hardware aufsetzen.
4. **Erst wenn Etappe 1 auf Prod läuft und angekündigt ist,** das Repo auf privat stellen.
5. README und Installationsanleitung: Neuinstallation mit Token. `install.sh` fragt ihn ab oder übernimmt ihn als Option.

### Nicht in dieser Spec

- Lizenzwechsel (das ist eine rechtliche Frage, Task a0699e9b, Anwalt).
- Module-, Plugin- und Theme-Repos privat stellen (eigene Entscheidung; die Technik aus Etappe 1 ist dafür vorbereitet).
- Schutz des Codes auf den Servern selbst (Verschleierung). Das bringt wenig und schadet der Fehlersuche.

## Akzeptanzkriterien

**Etappe 1**
- Der Token wird verschlüsselt gespeichert. Er steht nie in einer API-Antwort, in `.git/config`, in einer Prozessliste oder im Log.
- „Zugang testen“ meldet alle vier Ergebnisse verständlich.
- `update.sh` funktioniert ohne Token wie bisher und mit Token gegen ein privates Test-Repo.
- Ein abgelehnter Pull führt zur Meldung „Zugang zum Code fehlt“ in der Konsole.
- Bestehende Installationen ändern sich durch das Update nicht. Ohne Token bleibt das Verhalten gleich.
- Getestet gegen ein privates Test-Repo mit einem Read-Nutzer, auf hydratest und im frischen 26.04-Container.

**Etappe 2**
- Buddy kann nur `read` vergeben. Das ist im Werkzeug fest verdrahtet und mit einem Test belegt.
- Pro Discord-Account gibt es höchstens eine Freischaltung. Neue GitHub-Konten (jünger als X Tage) werden abgelehnt, mit Grund.
- Die Liste in der Konsole stimmt mit GitHub überein. Entfernen in der Konsole entfernt auch auf GitHub.

## Offene Punkte für Till

- Name der Organisation.
- Mindestalter des GitHub-Kontos: Standard 30 Tage, passt das?
- Eigener CI-Runner, ja oder nein? Das kann bis Etappe 3 warten.
