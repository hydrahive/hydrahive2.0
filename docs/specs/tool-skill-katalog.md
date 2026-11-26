# Tool- und Skill-Katalog – kleiner Kern, Rest bei Bedarf

Stand: 26.11.2026 · Status: **Entwurf, wartet auf Freigabe** · Task: 2da6ec55 (Weg A) · Gespräch: Buddy-Session 26.11.

## 1. Absicht und Warum

Till (26.11.): „Wie man gezielt viele hundert effektive Tools und Skills bauen kann für alles mögliche an Arbeiten, ohne dass es enorm an Tokens kostet.“ Drei Gründe, alle gleich wichtig:

1. **Kosten.** Jeder Agent bekommt heute bei jedem LLM-Aufruf seine komplette Tool-Liste und die Skill-Tabelle.
2. **Falsche Tool-Wahl und Trägheit.** Viele ähnliche Tools verwirren das Modell.
3. **Wachstum.** Hunderte Spezial-Tools (u. a. sparsame Linux-Tools) passen heute schlicht nicht in den Prompt.

Dazu: Ein Agent soll seinem Unteragenten **pro Auftrag** genau die Tools und Skills mitgeben können, die die Aufgabe braucht.

### Messung (.4, 26.11.2026)

| Was | Wert | Quelle |
|---|---|---|
| Tools bei till's Buddy | 158 (Assistenten/andere Buddys 91–98, Projekt-Agent 71) | `agents/*/config.json` |
| Tools tatsächlich benutzt, 30 Tage, alle Agenten | **46** verschiedene; `shell_exec`/`file_*` = 82 % aller 13.105 Aufrufe | `tool_calls` |
| Kern-Tools allein (46) | ≈ 9.400 Tokens; größtes `ask_agent` ≈ 1.100 | Schemas aus `REGISTRY` |
| Grundlast je Aufruf (kleinster Prompt) | Buddy ≈ 56.000, Projekt-Agent ≈ 18.000 Tokens | `llm_calls` |
| Schnitt je Aufruf | Buddy ≈ 354.000, Projekt-Agent ≈ 392.000; aus dem Cache 92 % / 79 % | `llm_calls` |

**Cache-Regel (Anthropic-Doku „Prompt caching → What invalidates the cache“, geprüft 26.11.):** Reihenfolge des Caches ist tools → system → messages; **jede Änderung an den Tool-Definitionen verwirft den ganzen Cache, auch den Verlauf.** Ein Nachladen mitten in einer Buddy-Sitzung kostet damit den Neuaufbau von im Schnitt ≈ 354.000 Tokens. Gleichzeitig kommt der Tool-Block heute zu 92 % (Buddy) aus dem Cache – die laufende Ersparnis pro Aufruf ist also kleiner als die rohe Token-Zahl (Rechnung nicht gemessen, nur abgeleitet).

**Einordnung (wichtig für die Erwartung):** Der Schnitt besteht fast nur aus Gesprächsverlauf. Der Katalog spart heute einen **Teil** der Grundlast (beim Buddy grob 25–35 k Tokens je Aufruf, geschätzt, nicht gemessen) – der große Gewinn ist das **Wachstum**: das 500. Tool kostet im Prompt nichts. Verlaufskosten löst der Katalog nicht (eigenes Thema).

## 2. Ziele, Nicht-Ziele, Anti-Ziele

**Ziele**
- Z1 Ein Agent startet mit einem **kleinen festen Kern** und lädt weitere Tools/Skills **gezielt** über eine Suche nach.
- Z2 Die Suche findet das passende Tool auch ohne exakten Namen („Bild machen“ → `generate_image`): **Bedeutungs- und Wortsuche kombiniert**.
- Z3 Ein Agent kann einem Unteragenten **pro Auftrag** Tools und Skills zuweisen – aus einem **Freigabe-Pool** (Till: Variante b).
- Z4 Funktioniert mit **allen** genutzten Modellen (Anthropic, MiniMax, Codex, LiteLLM-Weg), nicht nur einem Anbieter.
- Z5 Neue Tools/Skills kommen **ohne Prompt-Kosten** dazu: Eintrag im Katalog genügt.

**Nicht-Ziele**
- Verlaufskosten (Kompaktierung) – eigenes Thema.
- Die Linux-Tools selbst bauen – kommt danach, profitiert hiervon.
- Prozess-Isolation von Modulen/Plugins (bleibt dokumentiertes Restrisiko).

**Anti-Ziele** (wäre ein Fehlschlag, obwohl es technisch läuft)
- A1 Agenten **finden ein vorhandenes Tool nicht** und arbeiten umständlich per Shell weiter oder geben auf.
- A2 Der Prompt-Cache bricht ständig, weil sich die Tool-Liste mitten im Lauf dauernd ändert – dann wird es **teurer** statt billiger.
- A3 Ein Unteragent bekommt über die Zuweisung **mehr Rechte**, als Till freigegeben hat (Shell-Sperre seit 20.11. muss halten).
- A4 Ein Lauf wird spürbar langsamer, weil vor jedem Schritt gesucht wird.

## 3. Grenzen und Vorgaben

- Die bestehenden Filter bleiben und gelten **auch für nachgeladene Tools**: Projekt-Einschränkung (`runner/_project_tool_scope.py`, inkl. Container-Allowlist), Besitzer-Freigaben (`access/tool_filter.py`), Shell-Sperre für Projekt-Agenten/Spezialisten.
- Nachladen darf **nie** ein Tool liefern, das der Agent laut seiner Freigabe nicht haben darf. Der Katalog ist eine **Suchhilfe**, keine Rechtequelle.
- Embeddings: vorhandene Infrastruktur (pgvector 0.8.1 im Postgres-Spiegel, Embed-Modell aus `llm` config). Ohne Postgres/Embed-Modell muss es **trotzdem** gehen (Wortsuche, Fallback „alles wie heute“).
- Abwärtskompatibel: bestehende Agenten-Configs laufen unverändert weiter, bis der Katalog-Modus je Agent eingeschaltet wird.

## 4. Ansätze

| | Weg | Kosten / Abwägung |
|---|---|---|
| **A** ✅ gewählt | **Kleiner Kern + Katalog-Suche** (`find_tools`/`find_skills`), nachgeladene Tools bleiben für die Sitzung, Zuweisung an Unteragenten aus Freigabe-Pool | Mittel bis groß; Cache bricht nur beim Nachladen (gebündelt, selten); Risiko A1 → Kategorien-Zeilen im Prompt |
| B | Feste Werkzeugkästen (Medien, Git, Haus …) ohne Semantik | Einfach, vorhersehbar, aber grob; bei Hunderten Tools wird auch die Kasten-Liste lang. **Wird als Kategorien-Ebene in A übernommen.** |
| C | Erst die Bremsen (träge Tools) | Erledigt am 26.11. (Postgres auf SSD, file-search 0.4.0); löst Wachstum nicht |
| — | Anthropics eingebaute Tool-Suche (`defer_loading`) | Verworfen als Hauptweg: nur Anthropic (Z4). Kann später als Optimierung für Claude-Modelle dazukommen. |

Till hat am 26.11. Weg A (mit B als Kategorien, nach C) und für die Zuweisung **Variante b (Freigabe-Pool)** gewählt.

## 5. Das Wie – was Till entschieden hat

- **E1 Zuweisung = Freigabe-Pool (b).** Ein Agent darf einem Unteragenten pro Auftrag Tools/Skills aus einem Pool geben, den Till pro Unteragent **oder** Projekt festlegt – auch Tools, die der auftraggebende Agent selbst nicht hat. Nichts außerhalb des Pools. (Nicht a: „nur eigene“; nicht c: „alles aus dem Katalog“.)
- **E2** Gesucht wird semantisch (Bedeutung) – Tills Ausgangsidee.

## 6. Vorschläge des Buddys (zum Gegenlesen – noch nicht von Till bestätigt)

- **V1 Eigener Katalog statt Anbieter-Feature** (wegen Z4).
- **V2 Kern-Set** (immer geladen, ≈ 12, aber nur soweit freigegeben – D6): `shell_exec`, `file_read`, `file_write`, `file_patch`, `todo_write`, `find_tools`, `find_skills`, `load_skill`, `ask_agent`, `read_memory`/`write_memory`/`search_memory`. Pro Agent erweiterbar („angeheftet“).
- **V3 Nachgeladen bleibt geladen** bis Sitzungsende (gegen A2). Nachladen gebündelt: `find_tools` darf mehrere auf einmal aktivieren. *(Durch die Cache-Regel fraglich – siehe F1.)*
- **V4 Kategorien-Zeilen im Prompt** (eine Zeile je Bereich, z. B. „Medien: Bild/Video/Musik/Sprache erzeugen“) gegen A1. Kategorien aus dem vorhandenen Feld `Tool.category` bzw. Modul-Zuordnung.
- **V5 Hybrid-Suche** über Name, Beschreibung, `prompt_hint`, Kategorie und Beispiel-Anfragen; Ergebnis: höchstens 5 Tools mit Kurzbeschreibung und Aktivieren in einem Schritt.
- **V6 Skills genauso**: Prompt zeigt statt der vollen Tabelle nur angeheftete Skills + Kategorien, `find_skills` sucht.
- **V7 Messung eingebaut**: je Sitzung festhalten, was gesucht, gefunden, aktiviert und benutzt wurde – so sieht man A1 (gesucht, nicht gefunden) und kann Beschreibungen nachschärfen.
- **V8 Einführung schrittweise**: Schalter je Agent (`tool_mode: classic | catalog`), zuerst ein Test-Agent, dann Spezialisten, zuletzt Buddys.

## 6a. Nach der Bauherren-Prüfung (26.11., hydrahive-reviewer, 9 Fragen)

Entscheidungen des Buddys (klein, ändern nicht, was gebaut wird – zum Gegenlesen):
- **D1 (Frage 1) Obergrenze bleibt die Freigabe des Agenten** (`agent.tools` + Freigabe-Pool, §5 E1). Der Katalog ist nur Suchhilfe (§3). Damit bei Hunderten Tools nicht jedes einzeln eingetragen werden muss: `agent.tools` darf ganze **Kategorien** freigeben (z. B. `kategorie:medien`) – gesetzt vom Admin/Besitzer wie heute.
- **D2 (Frage 3) Zuweisung kommt dazu, ersetzt nicht:** Unteragent = eigene Freigabe + aus dem Auftrag zugewiesene Tools ∩ Pool. Ohne `tools` im Auftrag wie heute. Föderierte Ziele (`persona@workstation`): keine Zuweisung (die Gegenstelle entscheidet). Spezialisten „auf Abruf“: wie alle. Abweichung von `bounded_tools` ist durch E1 gewollt.
- **D3 (Frage 5)** Plugin-Tools kommen in den Katalog (lokal, statisch). **MCP bleibt in Stufe 1 klassisch** (Schemas live je Lauf, je Nutzer/Projekt verschieden).
- **D4 (Frage 6) Gedächtnis-Sicht nach der möglichen Freigabe**, nicht nach dem Geladenen: Kann ein Agent ein Außen-Tool bekommen (Config oder Pool), gilt er als „nach außen“ (`db/_mirror_scope.py`). Vorsichtige Richtung.
- **D5 (Frage 7) Skills bekommen keine Rechte:** Sichtbarkeit wie heute (System/Nutzer/Projekt/Agent, `disabled_skills`), Index je Besitzer und Projekt getrennt; der Skill-Pool ist eine Vorauswahl.
- **D6 (Frage 8) Kern = Kern-Liste ∩ Freigabe** – der Kern erweitert nie Rechte (z. B. kein `shell_exec` für den Helpdesk-Agenten).

Offen für Till (ändern, was gebaut wird):
- ~~F1~~ → **E4 (Till, 26.11.: „auf jeden Fall b, Cache brechen geht gar nicht“): Die Tool-Liste ändert sich innerhalb eines Laufs NIE.**
  - Ein gefundenes Tool wird im laufenden Lauf über das feste Kern-Tool **`run_tool(name, args)`** aufgerufen. `find_tools` liefert dazu Name, Kurzbeschreibung und Parameter-Schema als Ergebnis (im Verlauf, nicht in der Tool-Liste).
  - `run_tool` prüft **genau dieselbe Freigabe** wie ein direkter Aufruf (Freigabe des Agenten inkl. Pool, Projekt-Scope, Besitzer-Freigabe, Shell-Sperre, Bestätigungspflicht `tool_confirmation`) und validiert `args` gegen das Schema. Kein Umweg an einer Prüfung vorbei.
  - **Fest dabei** ist ein Tool erst ab dem **nächsten Lauf**: beim Buddy ab der nächsten Nutzer-Nachricht (die Liste darf sich dann ändern, weil der Cache ohnehin mit der neuen Nachricht weiterläuft – *Annahme, im Plan nachzumessen*), bei Unteragenten ab ihrem Auftrag (`ask_agent` `tools`).
  - Damit entfällt V3 („nachgeladen bleibt bis Sitzungsende“) in dieser Form; stattdessen: was in einer Sitzung per `run_tool` benutzt wurde, wird für die nächsten Läufe vorgemerkt, mit Obergrenze (Frage 9).
  - Abnahme K4 neu: **Innerhalb eines Laufs ist die Schema-Liste byte-gleich** (Test: alle LLM-Aufrufe eines Laufs mit `find_tools`+`run_tool` haben identische `tools`).
- ~~F2~~ → **E3 (Till, 26.11.): Den Freigabe-Pool legt jeder Besitzer für seine eigenen Agenten fest** (nicht nur Admins). Gedeckelt durch die Rechte des Besitzers (`access/tool_filter.py`). *Annahme des Buddys, von Till nicht ausdrücklich bestätigt:* Projekte dürfen den Pool nur **einschränken**, nie erweitern – wie heute (`_project_tool_scope.py`).

Damit sind alle Fragen beantwortet. Als Nächstes liest **hydrahive-security-reviewer** das Design (Rechte: D1, D2, D4, F2).

## 7. Der Umsetzung überlassen

Tabellen-/Spaltennamen, Form des Index (eigene Tabelle im Spiegel vs. Datei), genaue Rangformel der Hybrid-Suche, Zahl der Treffer, wie das Aktivieren im Runner technisch wirkt (Schema-Liste je Iteration neu aus „Kern + aktiviert“), UI für den Freigabe-Pool, Reihenfolge der PRs.

## 8. Abnahme-Punkte

- **K1** Mit `tool_mode: catalog` schickt der Runner nur Kern + angeheftete + in dieser Sitzung aktivierte Tools an das Modell (Test: Schema-Liste im Payload).
- **K2** `find_tools` findet bei 10 vorgegebenen Alltagsanfragen (Liste im Test) das richtige Tool unter den ersten 3 – mit und ohne Embed-Modell (ohne: Wortsuche).
- **K3** `find_tools` liefert/aktiviert **nie** ein Tool außerhalb der Freigabe des Agenten (Projekt-Scope, Besitzer-Freigabe, Shell-Sperre) – Test mit gesperrtem Tool.
- **K4** Innerhalb eines Laufs ist die an das Modell geschickte Tool-Liste byte-gleich, auch wenn `find_tools`/`run_tool` benutzt werden (E4). Per `run_tool` Benutztes wird für Folgeläufe vorgemerkt (mit Obergrenze).
- **K10** `run_tool` lehnt alles ab, was ein direkter Aufruf ablehnen würde (Freigabe, Projekt, Besitzer, Shell-Sperre, Bestätigung), und validiert `args` gegen das Schema – Test je Sperrgrund.
- **K5** `ask_agent` nimmt `tools`/`skills` an; der Unteragent bekommt genau die Schnittmenge aus Anfrage und Freigabe-Pool, außerhalb des Pools wird abgelehnt mit Grund.
- **K6** `find_skills` + verkürzte Skill-Liste im Prompt funktionieren analog (K1/K2 für Skills).
- **K7** `tool_mode: classic` verhält sich exakt wie heute (bestehende Runner-Tests grün).
- **K8** Messung: gesucht/gefunden/aktiviert/benutzt je Sitzung abrufbar.
- **K9** Ohne Postgres/Embed-Modell kein Fehler: Wortsuche, notfalls classic.
