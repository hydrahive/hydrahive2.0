# Spec: Weniger Rückfragen bei shell_exec, Warten statt Ablehnen

Task d085a8cc. Till am 11.10.2026: „ich hasse diese bestätigungen wenn ich nicht da bin“. Freigegeben: Punkte 1 bis 3
(„j1 auch mitbeheben, 2 und 3 darfst du gleich mit machen“).

## Befund

- Die Rückfragen kommen vom Harakiri-Schutz in `shell_exec` (`tools/_protected_paths.py`, `shell_confirm_reason`).
  `require_tool_confirm` ist dafür nicht verantwortlich.
- Gemessen in `sessions.db`, nur lesend, Zeitraum 20.09. bis 11.10.2026: 29 echte „Vom Benutzer abgelehnt“ bei
  `shell_exec`. Jeder Befehl wurde mit dem heutigen Code erneut geprüft:

  | Anzahl | Meldung | Ursache |
  |---|---|---|
  | 22 | Schreibzugriff auf `/dev` | Steht `2>/dev/null` direkt vor `)` oder einem Backtick, nimmt der Redirect-Scan die Klammer ins Ziel auf (`/dev/null)`). Dann greift die Ausnahme für `/dev/null` nicht. |
  | 1 | Schreibzugriff auf `/opt` | `sed -i 's#rm -rf /opt/x …#' datei`: Die Wörter im sed-Ausdruck gelten als Datei-Argumente. |
  | 2 | Zugriff auf Geheimnis | Python-Code im Heredoc (`cat > test.py <<'EOF'`): `r.key` sieht aus wie eine Schlüsseldatei `*.key`. Heredoc-Zeilen werden wie Shell-Befehle geprüft. |
  | 1 | Zugriff auf Geheimnis | `/etc/sudoers.d/` in `incus exec hh-sudotest -- …`. Der Pfad liegt in einem Wegwerf-Container, nicht auf dem Host. |
  | 1 | Zugriff auf Geheimnis | `/api/.env` als URL-Pfad in einer Schleife. Bleibt so, weil der Fall selten ist. |
  | 2 | berechtigt | `rm -rf … /etc/hydrahive2/discord/…` und `touch /home/hydrahive/.ssh/probe` |

- Nach 300 s ohne Antwort liefert `tool_confirmation.wait` „deny“. Der Agent bekommt „Vom Benutzer abgelehnt“, auch
  wenn niemand am Rechner war.

## Was

### 1. Fehlalarme beheben (PR 1)

a) **Umleitungen:** Das Ziel einer Umleitung endet vor `)`, `` ` `` und `<`.
   - `x=$(cmd 2>/dev/null)` löst keine Rückfrage mehr aus.
   - `x=$(cmd > /etc/y)` löst weiterhin eine aus.

b) **Datei-Argumente** lokaler Befehle werden so gelesen wie von der Shell: Ein Text in Anführungszeichen ist ein Wort.
   Sind die Anführungszeichen unvollständig, bleibt es beim bisherigen Verfahren.
   - `sed -i 's#/opt/a#/opt/b#' datei` löst keine Rückfrage mehr aus.
   - `rm -rf "/opt/x"` und `sed -i 's/a/b/' /etc/hosts` lösen weiterhin eine aus.
   - Das gilt nur für die Schreib-Prüfung. Die Geheimnis-Prüfung bleibt unverändert.

c) **Heredoc-Inhalt** ist Text für einen Befehl und kein Shell-Befehl. Er wird nur noch geprüft, wenn im Befehl ein
   Programm steht, das Shell-Text ausführt: `bash`, `sh`, `zsh`, `dash`, `ksh`, `mksh`, `fish`, `busybox`, `su`,
   `sudo`, `doas`, `ssh`, `at`, `batch`, `crontab`.
   - Bei allen anderen Befehlen wird der Inhalt übersprungen, etwa bei `cat > x.py`, `python3 -` oder `git commit -F -`.
   - Was nach dem Ende-Marker folgt, wird wieder normal geprüft.
   - Steht ein solches Programm irgendwo in der Zeile, wird der Inhalt geprüft, auch hinter einer Pipe
     (`cat <<EOF | bash`).
   - Bewusst in Kauf genommen:
     - Ein Geheimnis-Pfad im Python-Heredoc löst keine Rückfrage mehr aus, zum Beispiel `open("/root/.ssh/id_rsa")`.
       Bisher fiel das nur zufällig auf, denn Python-Code versteht der Schutz ohnehin nicht.
     - Ein Skript, das erst per Heredoc in eine Datei geschrieben und später gestartet wird, prüft der Schutz nicht.
       Das passt zur bisherigen Einordnung: eine Bremse gegen Unfälle, keine Mauer.

### 2. Befehle in Containern (PR 2)

- `incus exec <name> [Optionen] [--] <befehl>` und `lxc exec …`: Der Befehl läuft im Container und nicht auf dem Host.
  Deshalb überspringt die Geheimnis-Prüfung seine Wörter. In den Container hinein schaut die Schreib-Prüfung schon
  heute nicht.
- **Ausnahme: HydraHives eigene Container.** Für sie bleibt alles wie heute.
  - Die Liste steht in der ENV `HH_PROTECTED_CONTAINERS`, Standard `hydrahive2-stt,hydrahive2-tts`.
  - Bei `remote:name` zählt der Name.
- Weiter geprüft wird alles, was die Shell auf dem Host ausführt, zum Beispiel:
  - Umleitungen außerhalb von Anführungszeichen, in beide Richtungen: `incus exec ct -- cat x > /etc/y` und
    `incus exec ct -- tee /x < /etc/shadow`
  - der zweite Befehl in `incus exec ct -- true; cat /etc/shadow`
- Enthält der Container-Befehl außerhalb von einfachen Anführungszeichen `$( … )`, Backticks oder `<( … )`, führt der
  Host diese Teile selbst aus. Dann gibt es keine Ausnahme, und der ganze Befehl wird wie heute geprüft.
- Ein Heredoc in einen solchen Container ist Container-Inhalt, zum Beispiel `incus exec ct -- bash <<'EOF'`. Er wird
  nicht als Host-Befehl geprüft.

### 3. Warten statt Ablehnen (PR 3)

- **Läufe im Chat-Fenster**, also Herkunft `chat` und `delegation` (Buddy, Projekt-Chat, Auswertung von
  Spezialisten-Ergebnissen):
  - Die Bestätigung wartet ohne Zeitlimit, bis Till entscheidet oder den Lauf stoppt.
  - ENV `HH_TOOL_CONFIRM_TIMEOUT_CHAT` in Sekunden, Standard `0` = ohne Limit.
- **Läufe ohne Fenster** (Zeitplan, Messenger, Spezialist per `ask_agent`, `inject`):
  - Das Limit bleibt, ENV `HH_TOOL_CONFIRM_TIMEOUT`, Standard `300`.
  - Nach Ablauf lautet das Ergebnis „Keine Antwort auf die Bestätigung – nicht ausgeführt“ statt „Vom Benutzer
    abgelehnt“.
- **Zurück am Rechner:**
  - `GET /sessions/{id}/run-status` liefert die offene Bestätigung mit (`pending_confirm`: `call_id`, `tool_name`,
    `arguments`, `reason`).
  - Beim Öffnen oder Neuladen der Sitzung zeigt die Oberfläche das Banner wieder an, auch wenn die Verbindung
    zwischendurch abgerissen war.
- **Stopp-Knopf:** bricht ab wie bisher. Die offene Bestätigung wird dabei aufgeräumt.
- **Hinweistext** bei „Tool-Bestätigung“ in den Agent-Einstellungen: Statt „Auto-Deny nach 5 Minuten“ steht dort das
  neue Verhalten.
- **Server-Neustart:** beendet den Lauf wie bisher.

## Nicht in dieser Etappe

- Was in `$( … )` steht, prüft der Schutz weiterhin nicht als eigenen Befehl. Das ist eine bekannte Lücke, kein
  Fehlalarm.
- `docker exec` und `podman exec`
- Schreib-Prüfung in HydraHives eigene Container hinein. Das wäre eine Verschärfung.
- Benachrichtigung, wenn ein Lauf auf eine Bestätigung wartet, zum Beispiel über Discord oder Push

## Umsetzung

- `tools/_shell_lex.py` (neu):
  - Hierher wandern `_split_top_level` und `_mask_quotes` aus `_protected_paths.py`, das heute 296 Zeilen hat.
  - Neu dazu kommen die Heredoc-Erkennung und `words()` (shlex mit Rückfall auf `split`).
- `tools/_container_exec.py` (neu, PR 2): erkennt `incus exec` und `lxc exec` und liefert den Containernamen und den
  Beginn des Container-Befehls.
- `runner/tool_confirmation.py`:
  - `register` speichert zusätzlich Session und Anzeige-Daten.
  - `wait(timeout=None)` wartet ohne Limit.
  - Neu: `pending_for(session_id)`.
  - Rückgabe `"timeout"` getrennt von `"deny"`.
  - Aufräumen bei Abbruch.
- `runner/_runner_tools.py`: Limit je Herkunft, eigene Meldung bei Ablauf
- `api/routes/sessions_messages.py`: `pending_confirm` in run-status
- Frontend:
  - `chat/api.ts`: Typ
  - `chat/_runFollow.ts`: Banner aus run-status
  - `i18n` `agents.json` (de/en): Hinweistext
- Settings: die beiden Limits

## Akzeptanz

1. Die 26 Fehlalarme aus der Messung lösen mit dem neuen Code keine Rückfrage mehr aus. Die 2 berechtigten tun es
   weiterhin. Gegenprobe gegen `sessions.db`, nur lesend.
2. Alle bestehenden Schutz-Tests bleiben grün. Der lokale Schutz bleibt also unverändert.
3. Ein Chat-Lauf mit offener Bestätigung wartet länger als das alte Limit und läuft nach „Erlauben“ weiter.
4. Ein Lauf ohne Fenster meldet nach Ablauf „Keine Antwort …“. Der Befehl wird nicht ausgeführt.
5. run-status liefert die offene Bestätigung. Nach dem Neuladen zeigt die Oberfläche das Banner. Geprüft mit vitest und
   echt im Browser auf hydratest.
6. Stopp während der Wartezeit beendet den Lauf, und es bleibt keine offene Bestätigung zurück.
