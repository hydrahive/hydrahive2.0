# Plan: Hilfe-Artikel nachziehen (Stand 28.11.2026)

> **Status:** FREIGEGEBEN (Till, 28.11.2026: „ok freigegeben“).
> Teil 1 zu `docs/specs/hilfe-guard.md`: erst den Rückstand aufholen, dann verhindert der Guard neue Lücken.
> Aufbau der Artikel nach `hydrahive2-modules/ziele/hilfe-aktuell.md` §2. Quellen kommen nur aus dem Code und den Specs auf `main`, Behauptungen werden am Code geprüft.

## 1. Was fehlt (geprüft am Code `main` 90a767b4)

| # | Artikel | Fehlt | Quelle |
|---|---|---|---|
| H1 | `help/de/agents.md` (zuletzt 14.11.) | Reiter **„Was darf der Agent?“**: Zweck-Satz und Vorschlag, die 28 Bereichs-Schalter mit Markierungen (⚠️ 🔒 💶), „teilweise“, Expertenansicht. Schalter **„Werkzeuge bei Bedarf suchen (spart Kosten)“**. Helfer-Schalter **„Darf bei Aufträgen zusätzliche Bereiche bekommen“**. Der Abschnitt „Tool-Set einschränken“ beschreibt noch die alte Liste. | `docs/specs/agent-bereiche.md` §2–4, `docs/specs/tool-skill-katalog.md` §5, `frontend/src/features/agents/areas/*` |
| H2 | `help/de/admin.md` § Updates (Text zum Update-Knopf ist da) | Was beim Update passiert: Sicherung vorher, Prüfung nach dem Neustart, **automatischer Rückweg** auf den alten Stand bei Fehlschlag. In der Oberfläche sichtbar ist das nur über das Update-Ergebnis (`HH-UPDATE-ENDE: fehler <Grund> – auf <Stand> zurückgesetzt`, ausgewertet in `frontend/src/shared/_updateLogStatus.ts`) – genau das erklären, mehr nicht. Kein Terminal-Hinweis (Regel Archiv-Texte 13.10.). | `docs/specs/update-rollback.md` §3, `installer/lib/update-rollback.sh`, `core/src/hydrahive/api/routes/system_admin.py` |
| H3 | `help/de/skills.md` (zuletzt 07.07.) | Mitgelieferte Arbeitsweisen-Skills (Superpowers v7, z. B. Brainstorming, Pläne schreiben, Fehlersuche, Prüfen vor dem Abschluss), wie sie an Agenten kommen (Katalog: `find_skills`/`load_skill` statt alles im Prompt) | `core/src/hydrahive/skills/system_defaults/` (z. B. `brainstorming.md`), `docs/specs/tool-skill-katalog.md`, PR #776/#777 |
| H4 | Modul-Hilfen | **Nicht** Teil dieses Plans. Die Modul-Zählung (2 von 87 PRs mit Hilfe) zeigt Rückstand, aber eine Bestandsaufnahme je Modul ist ein eigener Auftrag (Folge-Task, Liste aus dem Probelauf HG4 des Guards). | – |

## 2. Vorgehen

1. Ein Kern-PR `docs/hilfe-nachziehen-2026-11` mit H1–H3. Nur Markdown, kein Code.
2. Jede Aussage hat eine Fundstelle im Code oder in der Spec. Nichts beschreiben, was nur in der Spec steht und nicht gebaut ist. Solche Stellen werden weggelassen und im PR genannt.
3. Keine Screenshots in diesem Schritt (die Hilfe-Artikel haben heute keine; Bilder wären ein eigenes Thema).
4. Review als Lese-Auftrag (`hydrahive-reviewer`): Stimmen die Texte mit dem Code?
5. Nach dem Merge baut `wiki.yml` Wiki und PDF neu. Danach prüfen: Wiki-Seiten Agenten, Admin-Cockpit und Skills zeigen den neuen Stand, und das PDF ist ersetzt.

## 3. Abnahme

| # | Prüfung |
|---|---|
| HN1 | `agents.md` beschreibt Bereiche, Werkzeuge bei Bedarf und Helfer-Schalter so, wie sie im Code heißen (Beschriftungen aus `i18n/locales/de` geprüft) |
| HN2 | `admin.md` beschreibt Sicherung, Prüfung und Rückweg ohne Terminal-Anweisung |
| HN3 | `skills.md` nennt die mitgelieferten Arbeitsweisen-Skills und den Weg über den Katalog |
| HN4 | Review ohne „muss“, `help/loader.test.ts` grün, Wiki-Bau grün, die drei Seiten im Wiki aktualisiert |
