# Plan: AI-Security-Modul vollständig ausbauen

## Ziel

Das installierbare `ai-security`-Modul bietet ein nutzbares Cockpit, einen runtime-neutralen Scanner-Adapter und sichere Scanpfade, ohne Docker-in-Docker oder einen Docker-Socket im HydraHive-Container.

## Festgelegte Architektur

- Hub-Modul bleibt die Installationsgrenze.
- HydraHive-Core startet keine privilegierte Fremdruntime.
- AI-Infra-Guard kann über einen explizit konfigurierten externen HTTP-Service angesprochen werden.
- Für lokale Ausführung ist ein dedizierter Node-/Compute-Prozess oder Incus-Container vorgesehen.
- Native Venv/CLI bleibt für statische Skill-/MCP-Scans möglich.
- Aktive Agent-/Jailbreak-Tests bleiben opt-in und getrennt von Read-only-Infrastruktur-Scans.

## Reihenfolge

### 1. Cockpit-Frontend

- [x] Health, Ziel-Allowlist, Scan starten, Status und Report anzeigen.
- [x] Nur Admin-Rolle sichtbar.
- [x] Polling mit Abbruch bei abgeschlossenem/fehlgeschlagenem Scan.
- [x] Keine Geheimnisse oder freien Ziel-URLs im Frontend.

### 2. Runtime-Vertrag ohne Docker

- [ ] Provider-Konfiguration für `external_http` und später `node_runtime` definieren.
- [ ] Node-/Compute-Job-Vertrag für einen nicht-interaktiven Scanner-Prozess spezifizieren.
- [ ] Ressourcenlimits, Workspace-Allowlist, Ergebnisgröße und Zeitlimit festlegen.
- [ ] Native Venv/CLI-Pilot für statische MCP-/Skill-Scans durchführen.

### 3. MCP-/Skill-Scans

- [ ] Nur freigegebene Workspace- oder Modulpfade.
- [ ] Archivgrößen- und Entpacklimits.
- [ ] Statische CLI-Ausführung ohne HydraHive-Agent-Kontext.
- [ ] SARIF-Import und Findings-Normalisierung.

### 4. AI-Infra-Scan erweitern

- [ ] Weitere freigegebene Komponenten und Zielprofile.
- [ ] Report-Normalisierung mit CVE, Schweregrad, Quelle und Fix-Hinweis.
- [ ] Keine automatische Remediation.

### 5. Aktive Tests

- [ ] Agent-/Jailbreak-Tests nur nach expliziter Zielbesitz-Bestätigung.
- [ ] Request-/Kostenlimits, Audit-Events und separate Berechtigung.
- [ ] Keine privaten Ziele ohne explizite Betreiberfreigabe.

### 6. Release-Gate

- [ ] Core-Kopie und Hub-Kopie synchron.
- [ ] Backend-, Modul- und Frontend-Tests grün.
- [ ] Security-Audit und HydraHive-Code-Review.
- [ ] Installieren, Deinstallieren, Neustart und fehlender Runtime-Dienst getestet.

## Nicht erlaubt

- Docker-in-Docker.
- Docker-Socket-Mount.
- beliebige Shell-Kommandos aus User-Input.
- freie Ziel-URLs ohne Allowlist.
- aktive Red-Team-Tests als Standardfunktion.
- automatische Änderungen an gescannten Systemen.
