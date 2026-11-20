# Ketten-Anker: Zielbild und Originalauftrag reisen unverändert mit

Stand 20.11.2026 · Till: „Das muss alles fest in HydraHive verankert werden, am besten nicht
Prompting, sondern Scripting, um das Driften zu vermeiden.“

## Befund („stille Post“)

Kette Buddy → Projekt-Agent → Spezialisten (Cryptoboard, Auftrag d6dfb7e9, 20.11.):

| Station | Text | fehlte |
|---|---|---|
| Buddy → Projekt-Agent | 8.101 Zeichen | 2 Kernpunkte |
| Projekt-Agent → Backend-Spezialist (neu formuliert) | 10.268 Zeichen | 6 Kernpunkte (u. a. „Zahlungen nicht angehakt“, Live-Prüfung) |
| Projekt-Agent → Frontend-Spezialist (neu formuliert) | 6.328 Zeichen | Zielbild komplett |

Jede Ebene schreibt den Auftrag neu; das eigentliche Ziel stand in keinem Auftrag. Ergebnis:
grüne Tests gegen das falsche Ziel, Fertig-Meldungen ohne Nutzen-Prüfung.

## Lösung (Etappe 1 – dieser PR)

**Im Code, nicht im Prompt.** Der Agent kann es weder vergessen noch abschalten.

- `agentlink/chain_anchor.py`: Zwei Blöcke mit festen Markern und SHA-256-Prüfsumme im Auftragstext:
  `ziel` (Zieldokument) und `original` (Originalauftrag). Ein Block mit falscher Prüfsumme gilt als
  nicht vorhanden (Manipulationsschutz), `strip` entfernt auch beschädigte Blöcke.
- `ask_agent` (nur interne Ziele, nicht beim Fortsetzen per resume_token) hängt die Blöcke an jeden
  Auftrag an (`tools/_ask_agent_anchor.py`):
  - **geerbt** aus dem eingehenden Auftrag der eigenen Session (Handoff-Lauf) – hat immer Vorrang,
    der Agent kann sie nicht ersetzen;
  - sonst **neu**: Originalauftrag = dieser Auftrag; Zieldokument aus dem neuen Feld `ziel_doc`
    (Pfad relativ zum Workspace, nicht außerhalb, max. 60.000 Zeichen).
  - `ziel_doc` angegeben, Datei fehlt/leer/außerhalb → Auftrag wird **nicht** abgeschickt.
- Empfang: `runner/_handoff_setup._remember_anchor` speichert die Blöcke des eingehenden Auftrags je
  Handoff (Migration `060_agent_handoffs_anchor.sql`, Spalten `anchor_ziel`, `anchor_ziel_quelle`,
  `anchor_original`); `db/agent_handoffs.anchor_for_session` liefert sie der nächsten Ebene.
- Warum nicht als AgentLink-Feld: Der AgentLink-Server speichert nur feste Felder
  (`AgentState`: task/context/knowledge/working_memory/handoff); `State.extra` wird gar nicht gesendet.
  Ein neues Feld ginge unterwegs verloren. Der Auftragstext kommt vollständig an.

## Tests

`tests/test_chain_anchor.py` (9): Roundtrip, Vorrang geerbter Blöcke, Manipulation, keine Verdopplung,
**zwei Ebenen mit umgeschriebenem Auftrag → Original und Ziel kommen wörtlich beim Spezialisten an**,
fehlendes/außerhalb liegendes Zieldokument → nichts gesendet.
Gegenproben: Anker in ask_agent aus → 4 rot; Vererbung aus → der Zwei-Ebenen-Test rot.

Live-Probe 20.11.2026 (nach Deploy): Buddy → Projekt-Agent → `hydrahive-backend-engineer`. Der
Projekt-Agent schrieb den Auftrag in eigenen Worten neu, ohne Kernpunkte; in der DB-Nachricht des
Spezialisten standen Zieldokument (`ANKER-7319`) und Originalauftrag (`Leuchtturm`) wörtlich, der
Spezialist nannte beides.

## Etappe 2 – Ziel-Pflicht für Projektarbeit

- `ask_agent` an einen **Projekt-Agenten** mit `task_type` `feature`/`bug_fix`/`refactor` ohne Ziel
  (weder geerbt noch `ziel_doc`) → abgelehnt, nichts gesendet. Fragen/Prüfungen (`research`, `review`)
  bleiben ohne Ziel möglich.

## Etappe 3 – Abnahme per Skript

- Abnahme-Punkte im Zieldokument: Tabellenzeilen `| A1 | … |` oder Listenpunkte `- P1 …`
  (`agentlink/acceptance.points_from_ziel`).
- Neues Feld `abnahme` (Liste von IDs). Hat das Ziel Punkte, ist die Auswahl **Pflicht**. Der Kern hängt
  die gewählten Zeilen wörtlich als dritten Block `abnahme` an (mit Prüfsumme und der Anweisung, am Ende
  eine Tabelle `| Punkt | Stand | Beleg |` zu liefern).
- In der Kette erbt jede Ebene den Abnahme-Block; sie darf ihn für einen Teilauftrag **nur einschränken**
  (Teilmenge), nie ausweiten. Ohne Angabe reist der volle Umfang mit.
- Empfang: Spalte `anchor_abnahme` (Migration 061). Beim Lauf-Ende prüft `runner/_handoff_acceptance`
  den Bericht: jeder Punkt braucht eine Zeile mit ✅ und nicht-leerem Beleg (maßgeblich ist die letzte
  Zeile je Punkt). Sonst Status **`incomplete`** („unvollständig“) statt `done`; das Prüfergebnis hängt
  am Bericht. Fehler/Pause bleiben unverändert; Aufträge ohne Abnahme verhalten sich wie bisher.
- Grenze (bewusst): Das Skript prüft Vollständigkeit und Form, nicht ob der Beleg wahr ist. Die
  Gegenprobe am echten System bleibt Aufgabe des Auftraggebers.

Tests: `tests/test_chain_acceptance.py` (14). Gegenproben: Kern-Abnahme aus → 2 rot; Ziel-Pflicht aus →
1 rot; Umfangsprüfung aus → 2 rot; `incomplete`-Zustellung aus → 1 rot.

## Offen

4. Anzeige im Agenten-Baum (Task 56afb402): Zieldokument und Abnahme-Stand je Kette.
