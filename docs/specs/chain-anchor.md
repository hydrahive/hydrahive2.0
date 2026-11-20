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

## Nächste Etappen (nicht in diesem PR)

2. **Pflicht** `ziel_doc` für Projektarbeit (Buddy → Projekt-Agent), Ablehnung ohne Ziel.
3. **Abnahme per Skript:** ABNAHME-Punkte des Zieldokuments maschinell prüfen; rote Punkte →
   Status „unvollständig“ statt „fertig“; Bericht enthält die Abnahme-Tabelle statt Nacherzählung.
4. Anzeige im Agenten-Baum (Task 56afb402): Zieldokument und Abnahme-Stand je Kette.
