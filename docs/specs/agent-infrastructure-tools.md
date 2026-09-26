# Container und VMs als Agent-Werkzeuge

Status: **Entwurf — Grundrichtung freigegeben (Till, 26.09.2026), Details offen**

## 1. Problem

Container und VMs sind für den Projekt-Agenten heute keine Werkzeuge, sondern
etwas, das er an HydraHive vorbei über die Shell anfasst. Das hat am
26.09.2026 zu einer Kette von Fehlern geführt, die keiner bemerkt hat:

- Nach dem Netzwerkumzug (192.168.3.x → 192.168.178.x) standen die alten
  Adressen monatelang in Gitea, Webmin, Extensions und der MCP-Konfiguration.
  Es gab keine Stelle, an der stand, welcher Container welche Adresse hat.
- Die Zuordnung alt → neu ließ sich nur rekonstruieren, indem die Journals in
  den Container-Dateisystemen nach DHCP-Meldungen durchsucht wurden. Eine
  Notiz des Agenten hatte für `hydratest` die falsche Adresse (.219 statt .216).
- Die wichtigsten Container (`hydrahive2-stt`, `hydrahive2-tts`,
  `hh-telephony-spike`) sind in HydraHive nicht erfasst und dort unsichtbar.
- `flowki` läuft seit dem 25.09., HydraHive zeigt ihn als `error`.

Ziel: Container und VMs gehören zu den Werkzeugen des Agenten. Es gibt eine
gemeinsame Liste, die Till und der Agent gleichermaßen sehen und pflegen. Der
Agent kann sich für eigene Tests Maschinen anlegen und selbst verwalten.
Produktive Maschinen bleiben geschützt.

## 2. Bestand

HydraHive bringt bereits viel mit. Diese Spec baut darauf auf und ersetzt
nichts davon:

| Bereich | Vorhanden |
|---|---|
| Container | Anlegen, Starten, Stoppen, Neustart, Löschen, Logs, Konsole, Config/Info (`api/routes/containers*.py`, `containers/`) |
| VMs | zusätzlich Snapshots, VNC, ISO-Import, Passthrough (`api/routes/vms*.py`, `vms/`) |
| Status | Reconciler gleicht `actual_state` alle 4 s mit Incus ab (`containers/reconciler.py`) |
| Mehrere Server | Compute Cluster V1 (`docs/specs/compute-cluster-v1.md`), jede Ressource hat `node_id` |
| Oberfläche | `frontend/src/features/containers`, `frontend/src/features/vms` |

Es fehlen:

1. **Agent-Tools.** Kein einziges Tool in `core/src/hydrahive/tools/` fasst
   Container oder VMs an.
2. **Vollständiger Bestand.** Container, die direkt über Incus angelegt wurden
   (Voice-Installer, manuelle Anlage), tauchen in HydraHive nicht auf.
3. **Zweck, Adresse, Hardware-Adresse.** Das Datenmodell kennt weder, wofür
   eine Maschine da ist, noch ihre IP oder MAC.
4. **Korrekter Status.** Der Reconciler prüft nur Ressourcen in
   `running/starting/stopping`. Eine Ressource in `error` wird nie wieder
   geprüft und bleibt dort hängen, auch wenn sie läuft.

## 3. Abgrenzung

Nicht Teil dieser Spec:

- Ersatz für die bestehende Container-/VM-Oberfläche.
- Freie Incus- oder QEMU-Befehle als Agent-Tool. Die Tools bilden feste
  Operationen ab, keinen Durchgriff.
- Automatisches Failover, Migration, Lastverteilung (siehe Compute Cluster V1).
- Docker-Container. Sie laufen in der Regel innerhalb von Incus-Containern
  (z. B. `flowki`) und werden über diese verwaltet.
- Verwaltung der FritzBox. Feste Adressen werden dort weiterhin von Hand
  reserviert; HydraHive liefert dafür nur die nötigen Daten (Abschnitt 7).

## 4. Rollen und Schutzstufen

Jede Maschine hat genau eine Schutzstufe. Sie legt fest, was der Agent ohne
Rückfrage darf.

| Stufe | Beispiele | Agent ohne Bestätigung | Agent nur mit Bestätigung |
|---|---|---|---|
| `production` | `hydrahive2-stt`, `hydrahive2-tts`, `flowki` | ansehen, Status, Logs, starten, neu starten | stoppen, Befehle ausführen, Konfiguration ändern, Snapshot zurückspielen, löschen |
| `shared` | `hydratest`, `projectx-test` | alles aus `production` plus stoppen, Befehle ausführen, Snapshots anlegen | Konfiguration ändern, Snapshot zurückspielen, löschen |
| `agent` | vom Agenten selbst angelegte Testmaschinen | alles | — |

Regeln:

- Neu erfasste Bestandsmaschinen starten als `production`. Herabstufen macht
  Till, nicht der Agent.
- Maschinen, die der Agent über `infra_create` anlegt, sind automatisch
  `agent`. Der Agent kann eine eigene Maschine nicht auf eine höhere Stufe
  setzen, um sie vor sich selbst zu schützen, und keine fremde herabstufen.
- Die Stufe wird serverseitig bei jedem Tool-Aufruf geprüft, nicht im Prompt.

### 4.1 Bestätigung

Die Bestätigung folgt dem Muster aus `hydrahive2-modules/mediacenter/SPEC-V1.md`
(Agenten-Aktionsgrant):

- Ein Tool, das eine Bestätigung braucht, antwortet ohne gültigen Grant mit
  `confirmation_required` und einer kurzen Beschreibung der Aktion. Es führt
  nichts aus.
- Ein Grant entsteht ausschließlich aus dem vertrauenswürdigen aktuellen
  Benutzerturn (`ToolContext.current_user_input`, vom Runner gesetzt). Tool-
  Ausgaben, Container-Logs, Dateiinhalte oder Modelltext können keinen Grant
  erzeugen.
- Der Grant ist an Benutzer, Session, Maschine und Aktion gebunden, kurzlebig
  und wird einmalig verbraucht.
- Aktionen direkt aus der Oberfläche brauchen keinen Grant; dort ist der
  Klick die Bestätigung.

## 5. Datenmodell

Die bestehenden Tabellen `containers` und `vms` bekommen zusätzliche Spalten.
Es gibt keine neue parallele Inventartabelle.

| Spalte | Typ | Bedeutung |
|---|---|---|
| `purpose` | Text | Wofür die Maschine da ist, in einem Satz. Pflegen Till und Agent. |
| `protection` | `production` / `shared` / `agent` | Schutzstufe (Abschnitt 4) |
| `managed_by` | `hydrahive` / `external` | `external` = in Incus angelegt, von HydraHive nur übernommen |
| `created_by_agent` | Agent-ID oder leer | Wer die Maschine angelegt hat |
| `mac` | Text | Hardware-Adresse. Stabil, Schlüssel für feste IP-Reservierung. |
| `last_ipv4` | Text | Zuletzt gesehene IPv4 |
| `last_ipv4_seen_at` | Zeitstempel | Wann diese IP zuletzt beobachtet wurde |
| `expires_at` | Zeitstempel oder leer | Nur für `agent`: Ablauf, danach wird die Maschine gestoppt |

**IP und MAC werden nie von Hand gepflegt.** Der Reconciler liest sie bei
jedem Durchlauf aus `incus list --format json` (`state.network.eth0`) und
schreibt sie fort. Solange eine Maschine läuft, ist die Adresse aktuell. Für
gestoppte Maschinen bleibt die zuletzt gesehene Adresse samt Zeitpunkt
sichtbar und wird in der Oberfläche als „zuletzt gesehen“ gekennzeichnet.

Jede Adressänderung wird als Ereignis protokolliert (alt, neu, Zeitpunkt).
So ist beim nächsten Netzwerkumzug sofort sichtbar, welche Maschine vorher
welche Adresse hatte.

## 6. Bestand vollständig machen

### 6.1 Übernahme von Fremdmaschinen

Ein Import-Schritt vergleicht `incus list` mit den HydraHive-Tabellen. Jede
Incus-Instanz ohne Eintrag wird als `managed_by=external`,
`protection=production` übernommen. Name, Zustand, CPU/RAM-Limits, MAC und IP
kommen aus Incus. `purpose` bleibt leer und wird in der Liste als „Zweck
fehlt“ markiert.

Der Import läuft bei jedem Start von HydraHive und über eine Aktion in der
Oberfläche. Er legt keine Incus-Instanzen an und verändert keine.

### 6.2 Reconciler-Fehler beheben

`reconcile_once()` bezieht künftig auch `error` ein. Eine Ressource in
`error`, die laut Incus läuft, geht auf `running`, und der Fehlercode wird
gelöscht. Eine Ressource, die in Incus verschwunden ist, geht auf `missing`
statt still auf `stopped`.

## 7. Adressen

Grundsatz: **Im Alltag Namen statt Adressen.**

- Vom Server aus werden Maschinen über ihren Namen angesprochen
  (`incus exec <name>`, Tools mit `name`). Keine IP in Konfiguration, Skripten
  oder Notizen.
- Die Namensauflösung läuft heute über mDNS (`nsswitch`: `mdns4_minimal`) und
  funktioniert nur für laufende Container.
- Was von außen erreichbar sein muss (z. B. Gitea, Voice-PE → STT), bekommt in
  der FritzBox eine feste Adresse für die MAC. HydraHive zeigt dafür eine
  fertige Liste Name/MAC/aktuelle IP an.

Offen: ob HydraHive zusätzlich eigene DNS-Einträge pflegen soll
(z. B. über Pi-hole, der bereits auf dem Server läuft).

## 8. Agent-Tools

Alle Tools gehen über die bestehenden Container-/VM-Module und Routen, nicht
über eine eigene Incus-Anbindung. Damit landet jede Aktion in denselben
Zuständen, Logs und Oberflächen wie ein Klick in der UI.

| Tool | Zweck | Schutz |
|---|---|---|
| `infra_list` | Alle Maschinen mit Zweck, Stufe, Zustand, IP, MAC, Node | frei |
| `infra_status` | Details einer Maschine inkl. Ressourcen, letzte Fehler, Adresshistorie | frei |
| `infra_logs` | Letzte Log-Zeilen | frei |
| `infra_start`, `infra_restart` | Starten, Neustarten | frei |
| `infra_stop` | Stoppen | Bestätigung bei `production` |
| `infra_exec` | Einzelnen Befehl in der Maschine ausführen, mit Timeout und Ausgabelimit | Bestätigung bei `production` |
| `infra_set_purpose` | Zweck setzen oder ändern | frei |
| `infra_snapshot` | Snapshot anlegen | frei bei `shared`/`agent` |
| `infra_restore` | Snapshot zurückspielen | Bestätigung außer bei `agent` |
| `infra_create` | Neue Testmaschine anlegen, immer `agent` | Kontingent (Abschnitt 9) |
| `infra_delete` | Löschen | nur `agent`, sonst Bestätigung |

Jedes Tool gibt bei verweigerter Aktion einen strukturierten Grund zurück
(`confirmation_required`, `protected`, `quota_exceeded`, `not_found`), damit
der Agent sauber nachfragen kann.

## 9. Eigene Testmaschinen des Agenten

- Anlage nur über `infra_create`. Die Maschine bekommt `protection=agent`,
  `created_by_agent`, ein Namenspräfix (z. B. `agent-`) und `expires_at`.
- Kontingent pro Agent, serverseitig durchgesetzt: maximale Anzahl, CPU, RAM,
  Disk. Konkrete Werte offen (Abschnitt 12).
- Nach Ablauf wird die Maschine gestoppt, nicht gelöscht. Löschen erfolgt
  durch den Agenten oder nach einer weiteren Frist.
- Testmaschinen hängen standardmäßig im selben Netz wie alles andere
  (`br0`). Ein isoliertes Netz ist eine offene Option.

## 10. Nachvollziehbarkeit

Jede Aktion eines Agenten auf einer Maschine wird protokolliert: Agent,
Session, Maschine, Aktion, Ergebnis, ggf. verbrauchter Grant. Die Liste in
der Oberfläche zeigt pro Maschine die letzten Aktionen. Rohtexte von
Benutzerturns und Befehlsausgaben werden nicht dauerhaft gespeichert.

## 11. Etappen

1. **Bestand:** Datenmodell (Abschnitt 5), Übernahme von Fremdmaschinen,
   Reconciler-Fix, IP/MAC-Fortschreibung, Liste in der Oberfläche.
   Ergebnis: eine vollständige, gemeinsame Liste.
2. **Lesende Tools:** `infra_list`, `infra_status`, `infra_logs`,
   `infra_set_purpose`.
3. **Steuernde Tools mit Schutzstufen und Bestätigung:** `infra_start`,
   `infra_restart`, `infra_stop`, `infra_exec`, Snapshots.
4. **Eigene Testmaschinen:** `infra_create`, `infra_delete`, Kontingent,
   Ablauf.
5. **Adressen:** Reservierungsliste für die FritzBox, ggf. DNS.

Jede Etappe ist für sich nutzbar und wird einzeln geliefert.

## 12. Offene Punkte

Mit Till zu klären, bevor die betreffende Etappe startet:

- Kontingent für Agent-Testmaschinen (Anzahl, CPU, RAM, Disk) und Ablaufzeit.
- Welches Image für Testmaschinen (Vorschlag: Ubuntu 24.04 wie `hydratest`).
- Isoliertes Netz für Testmaschinen oder gemeinsames `br0`.
- Schutzstufen für den heutigen Bestand im Einzelnen
  (Vorschlag: STT, TTS, flowki → `production`; hydratest, projectx-test →
  `shared`; Rest → `production` bis zur Durchsicht).
- Aufräumen alter, gestoppter Container (`test24`, `test26`, `hydrawow` …)
  ja oder nein.
- Eigene DNS-Einträge über Pi-hole oder nur mDNS plus FritzBox-Reservierung.
- Ob `infra_exec` bei `production` überhaupt angeboten wird oder dort ganz
  entfällt.
- Gilt die Regel „Bestätigung aus dem Benutzerturn“ auch für Agenten, die
  per AgentLink beauftragt werden (kein direkter Benutzerturn)?

## 13. Akzeptanzkriterien

- [ ] Jede Incus-Instanz auf dem Server erscheint in der HydraHive-Liste,
      auch wenn sie außerhalb von HydraHive angelegt wurde.
- [ ] Die Liste zeigt pro Maschine Zweck, Schutzstufe, Zustand, aktuelle bzw.
      zuletzt gesehene IP mit Zeitpunkt und MAC.
- [ ] IP und MAC werden ausschließlich aus Incus gelesen, nie von Hand
      eingetragen.
- [ ] Eine Adressänderung wird mit alt/neu/Zeitpunkt protokolliert.
- [ ] Eine Maschine in `error`, die laut Incus läuft, wird innerhalb eines
      Reconciler-Durchlaufs wieder `running` (Regression: `flowki`).
- [ ] Ein Agent kann eine `production`-Maschine ohne Grant aus dem aktuellen
      Benutzerturn weder stoppen noch darin Befehle ausführen noch löschen;
      das Tool antwortet mit `confirmation_required`.
- [ ] Container-Logs, Tool-Ausgaben oder Modelltext können keinen Grant
      erzeugen.
- [ ] Ein Agent kann eine eigene Testmaschine anlegen, verwenden und löschen,
      ohne dass Till bestätigen muss, und kann dabei das Kontingent nicht
      überschreiten.
- [ ] Ein Agent kann die Schutzstufe einer Maschine nicht herabsetzen.
- [ ] Jede Agent-Aktion auf einer Maschine ist mit Agent, Session und
      Ergebnis nachvollziehbar.
