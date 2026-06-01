# HH2 Max-Effort Audit — Master-Index (2026-06-02)

Multi-Agent-Audit über die ungeprüften Hochrisiko-Flächen + ganze Codebase.
3 Phasen, ~75 Agenten, ~3,8M Tokens. Jeder Befund adversariell gegengeprüft (Skeptiker hat 4 verworfen).

**Gesamt: 57 bestätigte Befunde → 29 GitHub-Issues (#177–#205).**

## Phase A — Security der Hochrisiko-Module (13 Befunde, #177–#189)
Module: vms, containers, communication, backup, agentlink, butler, datamining.
- 🔴 **CRITICAL ×2:** #177 AgentLink unauth Handoff startet Runner (RCE-Klasse) · #178 Butler-Webhook führt Flows ALLER Owner aus (Tenant-Isolation gebrochen)
- 🟠 **HIGH ×6:** #179 VM-ISO Path-Traversal (Host-File-Read) · #180 Webhook-Secret nicht konstant-zeitig · #181 Node-Bridge ohne Auth · #182 Backup-Restore Symlink-Escape (filter=tar) · #183 User-Restore ohne Owner-Check · #184 AgentLink Response-Spoofing
- 🟡 **MEDIUM ×4:** #185 Container-Image Arg-Injection · #186 AgentLink-Architekturgrenze verletzt · #187 Butler-SSRF http_post · #188 toter webhook_secret
- 🟢 **LOW ×1:** #189 Restore ohne Größenlimit
- Verworfen: VM-Comma-Injection (Datei muss existieren), datamining-SQL (parametrisiert).
- Voller Detail-Report: `2026-06-02-security-audit-phase-a.md`

## Phase B — Tote/kaputte Verdrahtung (25 Befunde, #190–#199)
- **Backend-Endpunkte ohne Aufrufer (einzeln):** #190 datamining git/jsonl/logs-Import · #191 datamining embed/rechunk · #192 streaming SSE-Progress (durch Polling ersetzt) · #193 butler /registry (Frontend umgeht es) · #194 butler /flows/dry_run · #195 patientenakte Multi-Patient-Familie
- **Gebündelt:** #196 4 tote Frontend-API-Methoden · #197 9 tote Exports/Komponenten · #198 4 tote Settings-Felder · #199 2 i18n-Lücken
- Klasse identisch zum i18n-Namespace-Fund: gebaut, nie eingehängt.

## Phase C — Code-Qualität (19 Befunde, #200–#205)
- #200 **DRY Runner** — Anthropic-Helfer dedupl., inkl. `_block_to_dict`-Drift = stiller Datenverlust im Streaming-Pfad (echter Bug, nicht Kosmetik)
- #201 **PG-Mirror verschluckt RuntimeError still** — erklärt rückwirkend den offenen Datamining-Backfill-Bug ([[project_datamining_live_ingest]])
- #202 Recall-Fehler im Runner verschluckt · #203 Health backfill_daily verschluckt Exception
- #204 5 weitere still-verschluckte Fehler (gebündelt)
- #205 **Test-Lücken** kritischer Pfade: Tool-Authz-Gate, API-Key-Verifikation, LLM-Failover (3× HIGH) + Runner-Abort, Tool-Confirm, AgentLink-Handoff

## Empfohlene Reihenfolge beim Abarbeiten
1. **CRITICAL zuerst** (#177, #178) — RCE-Klasse + Tenant-Bruch
2. **HIGH security** (#179–#184) — alle an der AgentLink/Inbound/Backup-Grenze
3. **#201** (Mirror-Logging) — löst einen bekannten Produktions-Bug nebenbei
4. **#205** (Tests) — bevor wir die Security-Fixes machen, Sicherheitsnetz für Runner/Authz
5. Rest nach Kapazität.
