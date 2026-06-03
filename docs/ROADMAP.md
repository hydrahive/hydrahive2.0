# HydraHive2 — Roadmap & Ideen-Backlog

> Tills Ideen festgehalten, damit nichts verloren geht (wie die Feature-Landkarte).
> **Status hier ≠ Zusage.** Das sind Richtungen; jede braucht vor dem Bau eine
> SPEC-Entscheidung + Design-Phase (Regel #4/#8). Erfasst 2026-06-03.

---

## 🧱 Architektur-Fundament: Modulsystem (Keystone)

**Idee (Till):** Features als austauschbare **Module** — je Modul ein eigenes Repo,
im HydraHive ein **Install/Uninstall-Knopf**. Installieren → alle Menüpunkte, API,
Dienste des Moduls erscheinen. Deinstallieren → alles wieder weg (inkl. Dienste,
z.B. der Matrix-Server beim Chat-Modul). Wie WordPress-Addons.

**Warum das der wichtigste Punkt ist:** Es ist die *Antwort* auf das HH1-Trauma
(Monolith durch unkontrolliertes Feature-Wachstum). Mit Modulen bleibt der Core
klein; alle App-Ideen unten werden Module statt Core-Ballast.

**Stand heute (was es schon gibt):**
- **Plugins** (`12-plugins.md`): können NUR Agent-Tools — kein UI/API/Auth.
  Genau deshalb konnte der Team-Chat KEIN Plugin sein.
- **Extensions**: installieren *Dienste* per Script (tuwunel!) inkl. Uninstall.
  Der „Dienst kommt mit / geht mit"-Teil existiert also bereits.

**Die Lücke = Voll-Stack-Modul:** UI-Routen + Nav + API-Router + DB-Migrationen +
Dienste + Permissions als EINE install/uninstall-bare Einheit, je eigenes Repo.

**Harte Teile (ehrlich):**
- Backend (API-Router dynamisch registrieren, Migrationen, Dienste via Extension-
  System): gut machbar.
- **Frontend ist die Knacknuss:** das Frontend ist ein *gebautes Bundle*. „Knopf →
  Menüpunkt erscheint" ohne Rebuild braucht Module-Federation/Runtime-Loading
  (komplex) ODER Rebuild beim Install. Pragmatischer v1: Frontend liefert Modul-UIs
  mit, schaltet sie nur sichtbar wenn installiert (Nav macht schon konditionales
  Gating). Echte Code-Isolation („Modul weg = Code weg") ist die Kür danach.
- DB-Migrationen pro Modul + sauberes Uninstall (Tabellen droppen = Datenverlust →
  mit Bedacht, evtl. „deaktivieren statt löschen" + expliziter Purge).

**Empfohlener Weg:** nicht alles auf einmal. (1) Modul-Vertrag definieren, (2) EIN
neues Feature als echtes Modul bauen (Proof), (3) Bestehendes (Chat etc.) nach und
nach migrieren. Eng mit dem User-/Gruppen-Management denken (Module deklarieren Rollen).

---

## Querschnitt-Features

| Feature | Kurz | Aufwand | Notiz |
|---|---|---|---|
| **User-/Gruppen-Management** | Rollen (admin / projektadmin / user / chatter …), Feature-Zuweisung pro Gruppe | mittel | baut auf Permissions-SSOT (`17-auth.md`); gehört zum Modul-Vertrag (Module bringen Rollen mit) |
| **Handy-Chatseite** | Eigenes Mobile-Layout, Session- + Projekt-Picker, fürs Arbeiten am Handy optimiert | mittel | eigenständig, geht ohne Modulsystem; hoher Alltagsnutzen |
| **Tailscale-Firewall** | Firewall-Regeln für das Tailnet | mittel | eher Infra-/Extension-Modul |

---

## 📦 Module-Backlog (werden Module, sobald das Modulsystem steht)

Klassische PIM-/Haushalts-Apps — ohne Modulsystem würden sie den Core wieder
zumüllen. Daher: Modulsystem ist die **Voraussetzung**.

| Modul | Inhalt |
|---|---|
| **Kalender** | Termine, Ansichten, ggf. CalDAV |
| **Kontaktverwaltung** | Adressbuch, ggf. CardDAV |
| **Terminplaner** | mit Ferien + Feiertagen |
| **Notizbuch / Einkaufszettel** | freie Notizen, Listen |
| **Haushaltsverwaltung** | Aufgaben/Inventar/Wartung |
| **Kontoführung / Buchhaltung / Steuern** | Finanzen, Belege, Steuer-Export |

---

## ✅ Erledigt / in Arbeit (Kontext)

- **Team-Chat (Matrix/tuwunel)** — Schicht 1 + Etappe 5a/5b/5c fertig; 5d (Presence)
  als Nächstes. Voll dokumentiert in [`feature-map/27-teamchat.md`](feature-map/27-teamchat.md).
  Genau dieses Feature wäre der **erste Migrations-Kandidat** fürs Modulsystem
  („/modul/chat" mit allem drin, inkl. tuwunel-Extension).
