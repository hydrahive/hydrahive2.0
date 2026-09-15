# Spec: Workstation-Client — zweite HydraHive-Installation mit Serverzugriff

**Stand:** 2026-08-29 · **Status:** Design (Brainstorming), noch nicht implementiert
**Verwandt:** `federation/registry.py`, `smbmounts/`, SPEC.md §Federation/Externe Instanzen

---

## Problem

Auf einer Arbeitsplatzmaschine im Intranet läuft eine zweite, frische
HydraHive-Installation ohne Projekte und ohne Daten. Sie soll

1. **eigene lokale Projekte** bearbeiten können (unabhängig, auch ohne Server),
2. **Projekte des Servers** bearbeiten können — inklusive Datenbestand,
3. **lokale Fähigkeiten** anbieten, die es nur am Arbeitsplatz gibt (Webcam,
   Mikrofon), die dem Server nicht zur Verfügung stehen.

Heute gibt es dafür keinen Weg. Federation kann ausschließlich
Server → Workstation rufen (`fetch_card`, `POST /remote/chat`, 102 Zeilen).
Die umgekehrte Richtung — Workstation greift auf Serverprojekte und
Serverdaten zu — existiert nicht.

## Ausgangslage (verifiziert 2026-08-29)

**Vorhanden und nutzbar:**

| Baustein | Ort | Zustand |
|---|---|---|
| Samba-Server | `smbd`/`nmbd` **aktiv**, v4.23.6 | läuft |
| Samba-Installer | `installer/modules/47-samba.sh` | patcht `smb.conf` über Aggregator-Index `_index.conf` |
| Rechtemodell | Setgid `2775`, Files `664`, Samba-User in Gruppe `hydrahive` | gelöst |
| SMB-Mount-Backend | `core/src/hydrahive/smbmounts/` (434 Z.) | Optionen-Whitelist, Regex-Validierung, Reconciler |
| Externe Instanzen | `POST /api/external-instances` | legt User + Agent + API-Key in einem Schritt an |
| Git-Anbindung | `projects/_git.py`, `_git_ops.py`, `_gitea.py` | lokales Gitea angebunden |
| Tailscale | `installer/modules/80-tailscale.sh` | vorhanden, im Intranet **nicht nötig** |

**Nicht vorhanden:**

- NFS-Server (`nfs-kernel-server` nicht installiert → SMB gewählt, s.u.)
- Client→Server-Richtung in Federation
- Jede Form von Remote-Projekt-Zugriff

## Architekturentscheidung: Zuständigkeit nach Datenart trennen

Der Datenbestand hängt **nicht** allein am Dateisystem. Deshalb greift ein
Mount allein zu kurz:

| Datenart | Liegt in | Zugriffsweg |
|---|---|---|
| Repos (`hydrahive2/`, Module …) | Git-Arbeitskopie | **git clone** auf die Workstation |
| Große Nicht-Repo-Daten (`media/`, `atelier/`, `research/`, `_db-backup/`) | Verzeichnis | **SMB-Mount** |
| Projekt-Metadaten (`config.json`, Members) | Verzeichnis | SMB-Mount **oder** API (lesend) |
| Sessions, `llm_calls`, Tasks, Datamining | **SQLite** `sessions.db` | **HTTP-API**, niemals Mount |
| Agenten-Configs | `agents/<id>/config.json` | HTTP-API |

**Harte Regel: SQLite nie über den Mount beschreiben.** Dateisperren
funktionieren auf Netzwerk-Dateisystemen nicht zuverlässig; zwei schreibende
Rechner führen zu Korruption der Datenbank. Der Server bleibt alleiniger
Schreiber. Die Workstation liest und schreibt Transaktionales ausschließlich
über die API.

**Repos gehören nicht auf den Mount.** `git status` prüft zehntausende
Dateien einzeln auf mtime/size/inode; Editoren mit Dateiüberwachung erzeugen
zusätzliche Last. Zwei Rechner im selben Arbeitsverzeichnis erzeugen
Zustände, die Git nicht vorsieht. Repos werden geklont und über
push/pull synchronisiert — der Weg, für den Git gebaut ist.

### Warum SMB und nicht NFS

NFS wäre für Git technisch besser (native POSIX-Metadaten, Symlinks,
Inodes — CIFS emuliert das nur). Ausschlaggebend dagegen:

- Samba läuft bereits, NFS ist nicht installiert.
- `smbmounts/` ist vorhanden, geprüft und hat ein durchdachtes Rechtemodell.
- NFS bräuchte neues Installer-Modul, neuen Backend-Code und ein
  UID-basiertes Rechtemodell (Workstation-Nutzer müsste UID von `hydrahive`
  teilen).
- Der NFS-Vorteil betrifft vor allem Git — und Git läuft nach dieser Spec
  gar nicht über den Mount. Damit entfällt das Hauptargument.

**Offen/ungemessen:** Die Trägheit von Git über CIFS ist hier *nicht*
gemessen, sondern aus dem Verhalten von Git und CIFS abgeleitet. Falls
Repos später doch gemountet werden sollen, vorher messen:
`git status` auf gemountetem Repo gegen lokalen Klon.

---

## Bausteine

Vier Stücke. **B4 ist unabhängig von B1–B3** und kann parallel laufen.

### B1 — WKS-Verbindung (Fundament)

Ein Workstation-Modul, das die Verbindung zum Server herstellt und hält.

- Serveradresse + API-Key hinterlegen, Verbindungsstatus anzeigen.
- Key wird über den vorhandenen `POST /api/external-instances`-Pfad erzeugt
  (legt User + Agent + Key an) — **kein zweiter Mechanismus**.
- Key verschlüsselt und mit `0600` ablegen, nie ans Frontend zurückgeben,
  nie loggen.
- Serverseitig: Widerruf muss **sofort** wirken, nicht erst beim nächsten Neustart.

**Akzeptanz:** Verbindung herstellbar und trennbar; nach Widerruf am Server
schlägt der nächste Zugriff der Workstation fehl; Key taucht in keinem Log
und keiner API-Antwort auf.

### B2 — Remote-Projektliste

Der Server liefert seine Projekte über API; die Workstation zeigt sie neben
den lokalen.

- Lokale und entfernte Projekte sind in der Oberfläche **eindeutig
  unterscheidbar** (Herkunft sichtbar).
- Rechte werden serverseitig geprüft — die Workstation sieht nur Projekte,
  auf die der hinterlegte Principal Zugriff hat. Keine clientseitige Filterung.

**Akzeptanz:** Ohne Serververbindung bleiben lokale Projekte voll nutzbar;
Remote-Projekte werden als „nicht erreichbar" gekennzeichnet, nicht
stillschweigend ausgeblendet.

### B3 — Mount-Verwaltung für Serverprojekte

`smbmounts/` so erweitern, dass ein Projektverzeichnis des Servers auf der
Workstation eingehängt wird (heute: externe Freigabe *in* ein Projekt —
also die Gegenrichtung).

- Nur Nicht-Repo-Daten mounten (s. Tabelle oben).
- Bestehende Optionen-Whitelist und Regex-Validierung übernehmen, nicht
  aufweichen.
- Zustände sichtbar: `unmounted` / `mounting` / `mounted` / `error`.
- Mount-Verlust darf die Anwendung nicht blockieren.

**Akzeptanz:** Datei über den Mount lesen und schreiben; Aushängen ist
idempotent; abgebrochene Verbindung führt zu sichtbarem Fehlerzustand, nicht
zu einem hängenden Prozess.

### B4 — Lokale Geräte-Module (Webcam, Mikrofon)

Reine Workstation-Module ohne Serverbezug.

- **Auslöserbasiert, kein Dauerstrom.** Bild wird auf Anforderung
  aufgenommen, nicht kontinuierlich analysiert.
  Begründung: Messung 2026-08-24 (Task `1f9ceb7e`) — 96 % der LLM-Kosten sind
  Kontexttransport. Bilder sind die schwerste Fracht darin.
- Kamerazugriff nur nach ausdrücklicher Freigabe, Aktivität sichtbar
  anzeigen.
- Aufnahmen standardmäßig lokal halten; Weitergabe an den Server ist eine
  bewusste Einzelaktion.
- Audioweg prüft zuerst, ob `core/hydrahive/voice/` (STT Wyoming Port 10300,
  TTS) wiederverwendbar ist, statt einen zweiten Pfad zu bauen.

**Akzeptanz:** Kamera lässt sich hart deaktivieren; ohne Freigabe kein
Zugriff; keine Aufnahme verlässt die Workstation ohne Nutzeraktion.

---

## Sicherheit

Ein Arbeitsplatzrechner ist das schwächste Glied der Kette.
„Wir sind im Intranet" begründet den Verzicht auf Tailscale — **nicht** den
Verzicht auf Authentifizierung.

- Eigener API-Key je Workstation, begrenzte Rechte, sofort wirksamer Widerruf.
- Samba-Zugangsdaten nicht im Klartext in Konfigurationsdateien, die ins Git
  geraten können.
- Kein Token in Git-Remote-URLs (vgl. Task `f240363d` — genau dieser Fall trat
  bereits auf), keine Secrets in systemd-Journal (vgl. Task `ae3f4e62`).
- Der Credential-Store des Servers wird **nicht** auf die Workstation
  gespiegelt.

## Nicht-Ziele

- Keine Replikation zweier Datenbestände, keine Konfliktauflösung.
- Kein Offline-Betrieb für Remote-Projekte (lokale Projekte bleiben offline nutzbar).
- Kein Schreibzugriff der Workstation auf `sessions.db` — weder direkt noch
  über den Mount.
- Kein Repo-Zugriff über SMB.
- Kein Tailscale im Intranet (bleibt für spätere externe Server verfügbar).
- Keine dauerhafte Kamera-/Mikrofonauswertung.

## Entschieden: eigene Agenten auf der Workstation

**Entscheidung (till, 2026-08-29): Die Workstation betreibt eigene Agenten.**
Sie steuert *nicht* die Agenten des Servers fern.

Begründung — lokale Fähigkeiten sind an die Instanz gebunden, nicht an den
Agenten:

- Ollama läuft über `api_base: http://localhost:11434` (siehe
  `docs/ollama-provider.md`). Ein Server-Agent hat kein `localhost` der
  Workstation und kann die lokale GPU grundsätzlich nicht erreichen — auch
  nicht per Fernsteuerung.
- Dasselbe gilt für Webcam, Mikrofon, `shell_exec` auf der Workstation und
  lokale Dateien außerhalb der Mounts. Ein ferngesteuerter Server-Agent würde
  bei jedem `shell_exec` auf dem *Server* landen — auf einer Workstation
  praktisch immer das Falsche.
- Kostenaspekt: lokale Ollama-Modelle kosten nichts. Bei 96 % Kontexttransport-
  Anteil (Messung Task `1f9ceb7e`) ist ein Agent, der Routinearbeit lokal
  erledigt und nur für schwere Aufgaben ein Cloud-Modell zieht, ein realer
  Hebel.

Daraus folgt das Bild:

```
Workstation-Agent
  ├─ eigenes LLM (Ollama lokal / eigene Cloud-Keys)
  ├─ eigene Sessions + eigene llm_calls  → eigene Kostenrechnung
  ├─ lokale Tools (Cam, Mikro, shell_exec, lokale Dateien)
  └─ arbeitet AUF Serverprojekten
       ├─ Dateien   → SMB-Mount / git clone
       └─ Metadaten → HTTP-API zum Server
```

### Folgen, die mitgebaut werden müssen

1. **Kostenrechnung zerfällt auf zwei Instanzen.** `llm_calls` liegt dann in
   zwei Datenbanken; eine Auswertung wie am 2026-08-24 zeigte nur noch die
   halbe Wahrheit. Der vorhandene `external-instances`-Pfad ist genau für
   Datamining-Spiegelung gedacht — von Anfang an mitdenken, nicht nachrüsten.
2. **Zwei Agenten am selben Projekt.** Für Repos löst Git das. Für Tasks,
   Sessions und Memory (die über die API zusammenlaufen) ist zu klären, wer
   schreibt, wenn beide gleichzeitig arbeiten.
3. **Schärferes Sicherheitsprofil.** Ein Workstation-Agent mit eigenen Tools
   *und* Zugriff auf Serverprojekte ist mächtiger als eine Fernbedienung. Der
   API-Key liegt auf einem Arbeitsplatzrechner — begrenzte Rechte und sofort
   wirksamer Widerruf sind Pflicht (B1).

## Offene Punkte

1. Reicht ein Mount pro Projekt, oder ein Sammelmount über alle Workspaces? (B3)
2. Git-über-CIFS: messen, falls Repos doch gemountet werden sollen.
3. Schreibkonflikt Tasks/Sessions/Memory bei gleichzeitiger Arbeit von
   Workstation- und Server-Agent am selben Projekt (Folge 2 oben).
