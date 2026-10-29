# Spec-Index

> Automatisch erzeugt aus Dateinamen, Git-Historie und Überschriften.
> Neu erzeugen: `python3 scripts/gen_spec_index.py`

135 Spezifikationen. Die Spalte **Status** zeigt nur, was die Spec
selbst im Kopf angibt — leer heißt: nicht angegeben, nicht automatisch geraten.

## Mehrteilige Reihen

Bei Reihen ist in der Regel der **letzte Teil** der aktuelle Stand;
frühere Teile beschreiben bereits umgesetzte Etappen.

### videocut

| Spec | Titel | Status | Zuletzt geändert |
|---|---|---|---|
| [`videocut-v1.md`](videocut-v1.md) | Videoschnitt V1 — Clip-Bibliothek + Clips auf Spur legen |  | 2026-07-12 |
| [`videocut-v2.md`](videocut-v2.md) | Videoschnitt V2 — Playback, Playhead & Transport |  | 2026-07-12 |
| [`videocut-v3a.md`](videocut-v3a.md) | Videoschnitt V3a — Justage-Fundament (A/B-Roll) |  | 2026-07-12 |
| [`videocut-v3b.md`](videocut-v3b.md) | Videoschnitt V3b — Schnittpunkte & Output-Assemblierung |  | 2026-07-12 |
| [`videocut-v3c.md`](videocut-v3c.md) | Videoschnitt V3c — Übergangseffekte je Schnittpunkt |  | 2026-07-12 |
| [`videocut-v6a.md`](videocut-v6a.md) | Videoschnitt V6a — WYSIWYG-Export entlang der Schnittpunkte + Download |  | 2026-07-12 |
| [`videocut-v6b.md`](videocut-v6b.md) | Videoschnitt V6b — Weiche Übergänge im Export |  | 2026-07-12 |

## Einzelne Spezifikationen

| Spec | Titel | Status | Zuletzt geändert |
|---|---|---|---|
| [`access-groups.md`](access-groups.md) | Freigaben und Gruppen — wer darf was nutzen und teilen |  | 2026-09-29 |
| [`access-groups-plan.md`](access-groups-plan.md) | Plan: Freigaben und Gruppen — Etappe 1 (Funktions-Freigaben) |  | 2026-09-29 |
| [`admin-cockpit-visual-system.md`](admin-cockpit-visual-system.md) | Admin-Cockpit Visual System |  | 2026-07-16 |
| [`agent-background-delegation.md`](agent-background-delegation.md) | Spec + Plan: Spezialisten im Hintergrund beauftragen (ask_agent) |  | 2026-10-01 |
| [`agent-infrastructure-tools.md`](agent-infrastructure-tools.md) | Container und VMs als Agent-Werkzeuge |  | 2026-09-26 |
| [`agent-integrity-layer.md`](agent-integrity-layer.md) | Agent Integrity Layer |  | 2026-09-24 |
| [`agent-language.md`](agent-language.md) | Spec: Antwortsprache für alle Agenten aus der Buddy-Einstellung |  | 2026-10-11 |
| [`agent-model-picker.md`](agent-model-picker.md) | Agent-Editor: Modellauswahl ohne Limit, nach Anbieter gruppiert |  | 2026-09-30 |
| [`agentlink-checkpoint-resume.md`](agentlink-checkpoint-resume.md) | AgentLink Checkpoint and Resume |  | 2026-09-25 |
| [`agentlink-runtime-profiles.md`](agentlink-runtime-profiles.md) | AgentLink Runtime Profiles |  | 2026-09-25 |
| [`agentlink-security.md`](agentlink-security.md) | AgentLink: Absicherung |  | 2026-09-29 |
| [`ai-security-module.md`](ai-security-module.md) | Spec: AI-Security-Modul mit AI-Infra-Guard |  | 2026-09-09 |
| [`anthropic-oauth-gui.md`](anthropic-oauth-gui.md) | Spec: Anthropic-OAuth-Login in der GUI freischalten (dritter Weg) |  | 2026-07-07 |
| [`apikeys-self-service.md`](apikeys-self-service.md) | API-Keys: selbst verwalten, aber nur mit Login-Sitzung |  | 2026-09-30 |
| [`archiv-system.md`](archiv-system.md) | Archiv- und Sicherungsspeicher (systemweit) |  | 2026-10-14 |
| [`buddy-codex-reasoning-effort-fix.md`](buddy-codex-reasoning-effort-fix.md) | Buddy Codex Reasoning Effort Fix |  | 2026-07-11 |
| [`buddy-idle-video.md`](buddy-idle-video.md) | Buddy-Aktionsvideos |  | 2026-07-14 |
| [`buddy-media-player.md`](buddy-media-player.md) | Buddy-Media-Player |  | 2026-09-12 |
| [`buddy-session-picker.md`](buddy-session-picker.md) | Buddy: frühere Unterhaltungen wieder aufrufen |  | 2026-10-03 |
| [`buddy-settings-cockpit.md`](buddy-settings-cockpit.md) | Buddy-Einstellungscockpit |  | 2026-07-26 |
| [`buddy-widget-effects-plan.md`](buddy-widget-effects-plan.md) | Plan: Buddy-Widget-Effekte |  | 2026-07-10 |
| [`butler-module-nodes.md`](butler-module-nodes.md) | Spec: Butler-Editor zeigt Bausteine aus Modulen | Freigegeben (Till, 25.10.2026: „wir müssen den Butler sogar erweitern … der Butler sollte die treibende | 2026-10-25 |
| [`butler-palette-webhook-cleanup.md`](butler-palette-webhook-cleanup.md) | Fix-Spec: Butler — Palette gegen Registry, Webhook benutzbar machen | Freigegeben (Till, 2026 | 2026-09-28 |
| [`central-configuration.md`](central-configuration.md) | Zentrale Konfiguration — ein Ort für alle Einstellungen |  | 2026-09-26 |
| [`chat-mobile-compact.md`](chat-mobile-compact.md) | Chat auf dem Handy: kompakter Kopf, kompakte Eingabe, Hilfe-Knopf in der Fußzeile |  | 2026-10-24 |
| [`chat-run-decoupled.md`](chat-run-decoupled.md) | Plan: Agent-Lauf vom Browser entkoppeln (+ echter Stop) |  | 2026-07-29 |
| [`chat-upload-safety.md`](chat-upload-safety.md) | Chat-Dateiupload: sichtbare Limits und sicheres Streaming |  | 2026-07-20 |
| [`chat-upload-safety-plan.md`](chat-upload-safety-plan.md) | Plan: Sicherer Chat-Dateiupload bis 100 MiB |  | 2026-07-20 |
| [`cockpit-followup-finish.md`](cockpit-followup-finish.md) | Plan: Cockpit-Folgearbeit Buddy + Header-Menüs |  | 2026-07-10 |
| [`cockpit-global-menus.md`](cockpit-global-menus.md) | Cockpit-Chrome P2: Apps, Benutzer und kontextuelle Hilfe |  | 2026-07-11 |
| [`cockpit-offline-first-activation-plan.md`](cockpit-offline-first-activation-plan.md) | Plan: Cockpit-Aktivierung offline-first |  | 2026-07-10 |
| [`cockpit-redesign-inventory.md`](cockpit-redesign-inventory.md) | Cockpit-Redesign Inventur |  | 2026-07-10 |
| [`cockpit-redesign-plan.md`](cockpit-redesign-plan.md) | Plan: Cockpit-Redesign |  | 2026-07-10 |
| [`cockpit-responsive-topbar.md`](cockpit-responsive-topbar.md) | Cockpit-Chrome P1: Responsive Topbar und Mobile-Navigation |  | 2026-07-11 |
| [`code-graph.md`](code-graph.md) | Code-Graph — Projekt-Codebase als navigierbarer Wissensgraph (Etappe 1) |  | 2026-07-13 |
| [`comfyui-workflows-pflichtfelder.md`](comfyui-workflows-pflichtfelder.md) | Mitgelieferte ComfyUI-Abläufe: Pflichtfelder vollständig |  | 2026-10-24 |
| [`compact-riesige-nachrichten.md`](compact-riesige-nachrichten.md) | Compact bei riesigen Einzelnachrichten |  | 2026-10-27 |
| [`compute-cluster-v1.md`](compute-cluster-v1.md) | HydraHive Compute Cluster V1 — Node Agent + Incus |  | 2026-07-19 |
| [`compute-cluster-v1-plan.md`](compute-cluster-v1-plan.md) | Plan: HydraHive Compute Cluster V1 |  | 2026-07-20 |
| [`container-nat-ports.md`](container-nat-ports.md) | Container auf VPS: NAT-Netz und Portfreigaben | freigegeben von Till · **Task:** fa358d87 | 2026-10-11 |
| [`dashboard-today-event-time.md`](dashboard-today-event-time.md) | Dashboard: „Heute“ und „7 Tage“ nach Ereigniszeit, deutscher Tag, Dollar |  | 2026-09-30 |
| [`datamining-access.md`](datamining-access.md) | Datamining-Zugriff je Agent (E0) |  | 2026-10-09 |
| [`datamining-gesamtindex.md`](datamining-gesamtindex.md) | Datamining-Gesamtindex: Volltext über alles + Hybrid-Suche |  | 2026-10-10 |
| [`datamining-volltext-werkzeuge.md`](datamining-volltext-werkzeuge.md) | Datamining: volle Werkzeug-Ausgaben in den Index (Teil B von Task 36caf245) |  | 2026-10-10 |
| [`deepseek-provider.md`](deepseek-provider.md) | DeepSeek als LLM-Anbieter – Spec |  | 2026-10-20 |
| [`design-consistency-migration.md`](design-consistency-migration.md) | Plan: Lokale Design-Konsistenz für Legacy-Routen |  | 2026-09-18 |
| [`dev-browser-nachinstallieren.md`](dev-browser-nachinstallieren.md) | Browser-Werkzeug: dev-browser bei Installation und Update sicherstellen |  | 2026-10-26 |
| [`discord-agent-tools.md`](discord-agent-tools.md) | Feature-Spec: Discord-Werkzeuge für Agenten | Freigegeben (Till, 2026 | 2026-10-12 |
| [`discord-attachments.md`](discord-attachments.md) | Feature-Spec: Bilder an Discord-Nachrichten (discord_post / discord_reply) |  | 2026-10-12 |
| [`discord-moderation-tools.md`](discord-moderation-tools.md) | Feature-Spec: Discord-Moderationswerkzeuge für Agenten | Freigegeben (Till, 2026 | 2026-09-27 |
| [`discord-server-admin-tools.md`](discord-server-admin-tools.md) | Feature-Spec: Discord-Serververwaltung für Agenten | Freigegeben (Till, 2026 | 2026-09-28 |
| [`files-access.md`](files-access.md) | /api/files – Zugriff nur auf eigene bzw. freigegebene Dateien |  | 2026-10-10 |
| [`full-cockpit-visual-migration.md`](full-cockpit-visual-migration.md) | Full Cockpit Visual Migration |  | 2026-09-18 |
| [`harakiri-confirm-noise.md`](harakiri-confirm-noise.md) | Spec: Weniger Rückfragen bei shell_exec, Warten statt Ablehnen |  | 2026-10-11 |
| [`host-selfheal-ubuntu-2604.md`](host-selfheal-ubuntu-2604.md) | Spec: Host-Self-Heal nach Ubuntu-26.04-Upgrade |  | 2026-09-01 |
| [`installer-core-first.md`](installer-core-first.md) | Spec: Installer – erst der Kern, Zusatz-Module später über die Oberfläche |  | 2026-10-11 |
| [`knowledge-spaces.md`](knowledge-spaces.md) | Wissensräume für Agenten (E1/E2) |  | 2026-10-09 |
| [`legacy-topnav-cockpit-alignment.md`](legacy-topnav-cockpit-alignment.md) | Legacy-Topnav auf Cockpit-Standard angleichen |  | 2026-09-18 |
| [`legacy-vs-cockpit-gap-audit.md`](legacy-vs-cockpit-gap-audit.md) | Funktionsaudit: altes Design vs. Cockpits |  | 2026-07-11 |
| [`lehren-mit-beleg.md`](lehren-mit-beleg.md) | Lehren mit Beleg – Konzept |  | 2026-10-20 |
| [`linked-projects.md`](linked-projects.md) | Verknüpfte Projekte: Projekt-Agent und Spezialisten lesen weitere Projekte |  | 2026-10-10 |
| [`live-embedding-catalog.md`](live-embedding-catalog.md) | Live-Embedding-Katalog |  | 2026-09-05 |
| [`llm-catalog-v2.md`](llm-catalog-v2.md) | LLM-Katalog V2 — Multi-Node-Modellkatalog und Capability-Verifikation |  | 2026-09-18 |
| [`llm-client-api-base.md`](llm-client-api-base.md) | llm.client: eigene Adresse des Anbieters (api_base) auch außerhalb des Agenten-Chats nutzen |  | 2026-10-17 |
| [`local-image-to-video.md`](local-image-to-video.md) | Plan: Lokales Image-to-Video mit Start-/Endbild |  | 2026-09-06 |
| [`local-media-model-switching.md`](local-media-model-switching.md) | Lokale ComfyUI- und Cloud-Medienmodelle gezielt auswählen |  | 2026-09-05 |
| [`local-media-runtime.md`](local-media-runtime.md) | Spec: Local Media Runtime |  | 2026-09-26 |
| [`local-video-backends.md`](local-video-backends.md) | Spec: Lokale Video-/Bild-Backends (ComfyUI + sd-server) |  | 2026-10-20 |
| [`mac-update.md`](mac-update.md) | macOS: Update-Verlauf, Python-Pakete, Frontend – Spec |  | 2026-10-21 |
| [`media-atelier-layout-mock.md`](media-atelier-layout-mock.md) | Media-Atelier Layout-Mock |  | 2026-07-11 |
| [`media-cockpit-data-fill-plan.md`](media-cockpit-data-fill-plan.md) | Plan: Media-Cockpit mit Leben füllen |  | 2026-07-10 |
| [`media-production-suite-plan.md`](media-production-suite-plan.md) | Plan: Media-Produktionssuite Punkte 1–6 |  | 2026-07-11 |
| [`media-project-data-model.md`](media-project-data-model.md) | Plan: Media-Projekt-Datenmodell und Workspace-Struktur |  | 2026-07-11 |
| [`media-prompt-archive.md`](media-prompt-archive.md) | Spec: Media-Promptarchiv |  | 2026-07-11 |
| [`media-trailer-workflow-recovery.md`](media-trailer-workflow-recovery.md) | Media-Trailer-Workflow Recovery |  | 2026-07-11 |
| [`media-ux-p2-1.md`](media-ux-p2-1.md) | Media UX P2.1: Asset-Picker und vollständige Shot-Bearbeitung |  | 2026-07-11 |
| [`media-workspace-navigation.md`](media-workspace-navigation.md) | Media-Cockpit: eindeutige Arbeitsbereiche |  | 2026-07-11 |
| [`mining-modul.md`](mining-modul.md) | Spec: Mining-Modul — GPU-Rechner im Netz für Kryptex verwalten | Design, Aufbau von Till freigegeben, noch nicht implementiert | 2026-10-03 |
| [`modul-ladeschleife.md`](modul-ladeschleife.md) | Modul-Listen erst beim Gebrauch lesen (Werkstatt schwarz) |  | 2026-10-24 |
| [`modul-liste-vereinheitlicht.md`](modul-liste-vereinheitlicht.md) | Spec: Modul-Verwaltung — eine Liste, Beschreibungen, kontextabhängige Buttons |  | 2026-07-07 |
| [`modul-update-alle.md`](modul-update-alle.md) | „Alle updaten“ bei Modulen: ein Ablauf, einmal bauen, einmal neu starten |  | 2026-10-24 |
| [`modul-update-unabhaengig-vom-browser.md`](modul-update-unabhaengig-vom-browser.md) | Modul-Install, -Update und -Deinstallation laufen zu Ende, auch ohne offenen Browser |  | 2026-10-17 |
| [`modul-updates.md`](modul-updates.md) | Spec: Modul-Update-Erkennung, Übersichtlichkeit & Footer-Indikatoren |  | 2026-07-07 |
| [`module-view-sandbox.md`](module-view-sandbox.md) | Modul-Ansichten im Chat (abgeschottet) – Spec |  | 2026-10-20 |
| [`ollama-model-manager.md`](ollama-model-manager.md) | Ollama-Modellmanager |  | 2026-08-31 |
| [`ollama-provider.md`](ollama-provider.md) | Spec: Ollama als LLM-Provider |  | 2026-07-24 |
| [`plugin-updates.md`](plugin-updates.md) | Plugins: neue Version anzeigen und aktualisieren – wie bei den Modulen |  | 2026-10-10 |
| [`project-actions-location.md`](project-actions-location.md) | Project-Cockpit: Fachaktionen aus der globalen Topbar verlagern |  | 2026-07-11 |
| [`project-audio-library.md`](project-audio-library.md) | Projektgebundene Audio-Bibliothek |  | 2026-09-12 |
| [`project-cockpit-agent-editor.md`](project-cockpit-agent-editor.md) | Vollständiger Agenten-Editor im Projekt-Cockpit |  | 2026-07-13 |
| [`project-cockpit-mobile-tabs.md`](project-cockpit-mobile-tabs.md) | Projekt-Cockpit: Reiter auf schmalen Bildschirmen |  | 2026-10-24 |
| [`project-cockpit-p1.md`](project-cockpit-p1.md) | Plan: Project-Cockpit P1 – Basisdaten, Notizen und Löschen |  | 2026-07-11 |
| [`project-cockpit-p2.md`](project-cockpit-p2.md) | Plan: Project-Cockpit P2 – Mitglieder und Spezialisten |  | 2026-07-11 |
| [`project-cockpit-p3.md`](project-cockpit-p3.md) | Plan: Project-Cockpit P3 – Server, VMs und Container |  | 2026-07-11 |
| [`project-cockpit-p4.md`](project-cockpit-p4.md) | Plan: Project-Cockpit P4 – Mounts und SMB |  | 2026-07-11 |
| [`project-cockpit-p5.md`](project-cockpit-p5.md) | Project-Cockpit P5: Audit, Statistiken und Sessions |  | 2026-07-11 |
| [`project-cockpit-p6.md`](project-cockpit-p6.md) | Project-Cockpit P6: Git- und Gitea-Detailverwaltung |  | 2026-07-11 |
| [`project-cockpit-p7.md`](project-cockpit-p7.md) | Project-Cockpit P7: Sichere Projektintegrationen |  | 2026-07-11 |
| [`project-handover.md`](project-handover.md) | Spec: Globale Projekt-Handover-Datei |  | 2026-07-11 |
| [`project-member-roles.md`](project-member-roles.md) | Spec: Projekt-Member-Rechte (Read / Write / Admin) |  | 2026-07-29 |
| [`prompt-archive.md`](prompt-archive.md) | Feature-Spec: Prompt-Archiv (Prompt Library) | Entwurf | 2026-06-25 |
| [`pytest-parallel.md`](pytest-parallel.md) | Testreihe auf mehreren Kernen (pytest-xdist) |  | ? |
| [`python-314-umstieg.md`](python-314-umstieg.md) | Umstieg auf Python 3.14 (Ubuntu 26.04) |  | 2026-10-12 |
| [`refusal-visible.md`](refusal-visible.md) | Lauf-Abbrüche sichtbar machen (refusal + Buddy-Fehleranzeige) |  | 2026-09-30 |
| [`repo-zugang.md`](repo-zugang.md) | Spec: Zugang zum Code über GitHub-Freischaltung (privates Repo) |  | 2026-10-15 |
| [`scheduled-agent-tasks.md`](scheduled-agent-tasks.md) | Spec: Wiederkehrende Agentenaufgaben und Heartbeat-Verwaltung |  | 2026-09-07 |
| [`server-migration-rsync.md`](server-migration-rsync.md) | Server-Migration: Voll-Klon per rsync (Server-zu-Server) |  | 2026-07-01 |
| [`server-peering.md`](server-peering.md) | Server-Kopplung: HydraHive ↔ HydraHive über Tailscale | Design, freigegeben in Grundrichtung (Option C, Rechte | 2026-10-04 |
| [`smb-mounts.md`](smb-mounts.md) | SMB-Mounts — Fileserver-Freigaben als Projekt-Ressource |  | 2026-06-27 |
| [`startdesktop.md`](startdesktop.md) | Startseite mit Bereichen und Bereichs-Leiste |  | 2026-10-24 |
| [`system-skills-update.md`](system-skills-update.md) | System-Skills aktualisieren, Admin-Änderungen schützen |  | 2026-09-30 |
| [`system-updates.md`](system-updates.md) | Systemupdates: das ganze System mit aktualisieren |  | 2026-10-26 |
| [`theme-editor.md`](theme-editor.md) | Theme-Editor & Ordner-Themes |  | 2026-07-02 |
| [`theme-templates-brainstorm.md`](theme-templates-brainstorm.md) | Brainstorm-Anker: Theme-Templates mit Platzhaltern |  | 2026-07-02 |
| [`theming-system.md`](theming-system.md) | Theme-System — installierbare Designs (WordPress-Prinzip) |  | 2026-07-02 |
| [`theming-system-etappe3.md`](theming-system-etappe3.md) | Theme-System Etappe 3 — Hub-Installer (WordPress-Gefühl) |  | 2026-07-02 |
| [`tool-gate-non-tool-models.md`](tool-gate-non-tool-models.md) | Tool-Gate für Modelle ohne Function-Calling |  | 2026-07-27 |
| [`ubuntu-2604-support.md`](ubuntu-2604-support.md) | Ubuntu 26.04 LTS Support | Installation auf 26.04 läuft fehlerfrei durch | 2026-08-19 |
| [`ui-standard.md`](ui-standard.md) | HydraHive-UI-Standard (Barrierefreiheit und Bedienbarkeit) |  | 2026-10-20 |
| [`update-git-sicher.md`](update-git-sicher.md) | Update: nichts mehr still verwerfen, nie auf einen fremden Branch springen |  | 2026-10-26 |
| [`uuid7-reihenfolge.md`](uuid7-reihenfolge.md) | IDs in derselben Millisekunde in Reihenfolge (uuid7) |  | 2026-10-24 |
| [`vault.md`](vault.md) | Vault: PIN-Sperre, Protokoll und Vault-Chat |  | 2026-10-12 |
| [`videocut-export-library.md`](videocut-export-library.md) | Videoschnitt — Export-Historie „Fertige Filme" |  | 2026-07-12 |
| [`videocut-trim-split.md`](videocut-trim-split.md) | Videoschnitt — Trim & Split (Feinschnitt) |  | 2026-07-12 |
| [`voice-bridge-update-dependency.md`](voice-bridge-update-dependency.md) | Voice-Bridge-Abhängigkeit updatefest installieren |  | 2026-08-20 |
| [`websearch-blocked-engines.md`](websearch-blocked-engines.md) | Websuche: gesperrte Suchanbieter erkennen, Installer-Pfad korrigieren |  | 2026-10-02 |
| [`websuche-kostenlos.md`](websuche-kostenlos.md) | Websuche verbessern – kostenlos |  | 2026-10-20 |
| [`workstation-client.md`](workstation-client.md) | Spec: Workstation-Client — zweite HydraHive-Installation mit Serverzugriff | Design (Brainstorming), noch nicht implementiert | 2026-08-29 |
