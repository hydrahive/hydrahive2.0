# Plan: Admin-Cockpit Visual System

## Ziel

Alle aus dem Admin-Cockpit erreichbaren Oberflächen verwenden ein verbindliches Cockpit-Design statt gemischter Legacy-Komponenten. Die Referenzetappe migriert System, Settings, Voice und alle im System-Overlay sichtbaren Unterkomponenten vollständig; Users, Containers und der Gesamtaudit folgen in getrennten PRs.

## Abhängigkeiten

1. Gemeinsame Admin-UI-Primitives müssen vor den Fachbereichen existieren.
2. System ist der Referenzbereich und muss vor Users/Containers visuell abgenommen werden.
3. Users und Containers dürfen danach parallel bzw. unabhängig migriert werden.
4. Der Abschluss-Audit beginnt erst nach den drei Fachbereichen.

## Dateien — Referenzetappe

### Neu

- `frontend/src/features/cockpit/admin/ui/AdminAction.tsx` — einfarbige Standard-, Primär- und destruktive Aktionen.
- `frontend/src/features/cockpit/admin/ui/AdminPanel.tsx` — Panel/Karten-Grundfläche.
- `frontend/src/features/cockpit/admin/ui/AdminStat.tsx` — neutrale Kennzahlkarte.
- `frontend/src/features/cockpit/admin/ui/AdminStatus.tsx` — semantischer Status mit Text/Icon/Punkt.
- `frontend/src/features/cockpit/admin/ui/AdminField.tsx` — Labels, Hilfe, Input-Klassen und Toggle.
- `frontend/src/features/cockpit/admin/ui/AdminDialog.tsx` — gestapelter Dialograhmen.
- `frontend/src/features/cockpit/admin/ui/AdminFeedback.tsx` — Lade-, Fehler- und Leerzustände.
- `frontend/src/features/cockpit/admin/ui/index.ts` — öffentliche Exporte.
- `frontend/scripts/check-admin-visual-system.mjs` — statischer Guard gegen zurückkehrende Legacy-Muster in migrierten Scopes.

### Geändert

- `frontend/package.json` — Guard-Script registrieren.
- `frontend/src/features/cockpit/CockpitButton.tsx` — Primary-Gradient durch Cockpit-Cyan ersetzen oder intern AdminAction angleichen.
- `frontend/src/features/cockpit/admin/SystemOverlay.tsx` — Referenzlayout, neutrale Stats, verschachtelte Settings.
- `frontend/src/features/cockpit/admin/SystemSettingsOverlay.tsx` — AdminField/AdminToggle/Panel.
- `frontend/src/features/system/StatCard.tsx` — durch AdminStat ersetzen bzw. neutralisieren.
- `frontend/src/features/system/HealthBar.tsx` — neutrale Panels, semantischer Status.
- `frontend/src/features/system/VoiceInstallModal.tsx` — AdminDialog/AdminCodeBlock-Stil.
- `frontend/src/features/system/AgentLinkCard.tsx`
- `frontend/src/features/system/_AgentLinkKnownAgents.tsx`
- `frontend/src/features/system/TailscaleCard.tsx`
- `frontend/src/features/system/_TailscaleConnectedView.tsx`
- `frontend/src/features/system/_TailscaleInviteSection.tsx`
- `frontend/src/features/system/_TailscaleLoginForm.tsx`
- `frontend/src/features/system/BridgeCard.tsx`
- `frontend/src/features/system/SambaCard.tsx`
- `frontend/src/features/system/BackupCard.tsx`
- `frontend/src/features/system/BackupRestoreModal.tsx`
- `frontend/src/features/system/MigrationCard.tsx`
- `frontend/src/features/system/MigrationModal.tsx`
- `frontend/src/features/system/_systemHelpers.tsx`
- `frontend/src/shared/RestartModal.tsx` — nur soweit aus System erreichbar und noch Legacy-Stil vorhanden.

Legacy-Routenseiten `SystemPage.tsx` und `SettingsPage.tsx` werden nicht als zweite Designimplementierung gepflegt. Sie sollen nach Möglichkeit die migrierten Inhaltskomponenten verwenden oder als direkte Route weiterhin funktionieren, ohne neue Legacy-Stile in den Admin-Erreichbarkeitsbaum einzuschleppen.

## Implementierungsreihenfolge

### Task 1: Statischer Visual-System-Guard

- [ ] Guard schreiben, der in explizit migrierten Dateien `rgbFor`, visuelles `--c`, `box`-Klassen, dekorative Gradients und nicht-semantische Domainfarben meldet.
- [ ] Guard gegen aktuellen Stand ausführen und ROT dokumentieren.
- [ ] `npm run check:admin-visual` registrieren.
- [ ] Guard-Liste nach jeder Etappe nur um vollständig migrierte Dateien erweitern.
- [ ] Commit: `test(admin): guard cockpit visual system`

### Task 2: Admin-UI-Primitives

- [ ] AdminAction, AdminPanel, AdminStat, AdminStatus, AdminField/AdminToggle, AdminDialog und AdminFeedback implementieren.
- [ ] Dialog mit `role=dialog`, `aria-modal`, benannter Überschrift und kontrollierbarem Schließen versehen.
- [ ] Normalen Aktivzustand/Fokus ausschließlich Cockpit-Cyan gestalten.
- [ ] CockpitButton-Primary-Gradient entfernen und Impact per TypeScript/Build prüfen.
- [ ] Guard + TypeScript ausführen.
- [ ] Commit: `feat(admin): einheitliche Cockpit-UI-Primitives`

### Task 3: System-Kopf, Statistiken und Settings

- [ ] SystemOverlay auf die Primitives umstellen.
- [ ] Alle dekorativen Stat-Glows entfernen.
- [ ] Health-Checks als semantische Erfolg-/Fehlerzustände erhalten.
- [ ] Settings-Button auf lokalen `showSettings`-State umstellen.
- [ ] SystemSettingsOverlay als gestapeltes Kind rendern.
- [ ] SettingRow auf AdminField/AdminToggle/Feedback umstellen.
- [ ] Bestehenden Follow-up-Task `d8da1b7c` nach Abschluss schließen.
- [ ] Guard + TypeScript + Build ausführen.
- [ ] Commit: `refactor(admin): System und Einstellungen vereinheitlichen`

### Task 4: Voice- und Systemaktions-Dialoge

- [ ] VoiceInstallModal auf AdminDialog und neutrale Logfläche umstellen.
- [ ] Sicherheitsverhalten bewahren: während Start/Lauf nicht schließbar.
- [ ] RestartModal, BackupRestoreModal und MigrationModal auf denselben Dialograhmen umstellen.
- [ ] Fehler/Erfolg/Laufend nur semantisch einfärben.
- [ ] Guard + TypeScript + Build ausführen.
- [ ] Commit: `refactor(admin): Systemdialoge ins Cockpit-Design migrieren`

### Task 5: Sämtliche System-Cards und Unterkomponenten

- [ ] AgentLink, Tailscale, Bridge, Samba, Backup und Migration auf AdminPanel/AdminAction/AdminStatus umstellen.
- [ ] Unterkomponenten für Login, Invite, Known Agents und Connected View mitmigrieren.
- [ ] `box`, `rgbFor`, `--c`, Zinc-Paralleldesign, Gradients und dekorative Domainfarben entfernen.
- [ ] Semantik prüfen: connected/healthy=success, running/pending=warning, error/offline=danger; normale Aktionen=Cockpit-Cyan/neutral.
- [ ] Guard um alle vollständig migrierten Systemdateien erweitern und grün ausführen.
- [ ] TypeScript, Scope-ESLint, Build und Offline-Check ausführen.
- [ ] Commit: `refactor(admin): Systemkarten visuell konsolidieren`

### Task 6: Browser-Verifikation und Referenz-PR

- [ ] App ohne Page-Errors booten.
- [ ] Eingeloggt System-Hauptansicht prüfen.
- [ ] Settings als Kind-Overlay öffnen/schließen und Elternzustand erhalten.
- [ ] Voice Confirm/Running/Done/Failed prüfen.
- [ ] System-Cards inklusive expandierter Formulare/Logs prüfen.
- [ ] Desktop und schmalen Viewport prüfen.
- [ ] `hh-review`, Security-Review nur bei Sicherheitsänderungen, anschließend PR.
- [ ] Task Etappe 1 abschließen.

### Task 7: Users

- [ ] Guard zunächst ROT gegen Users-Erreichbarkeitsbaum ausführen.
- [ ] UsersOverlay, Dialoge und ApiKeysSection auf Primitives migrieren.
- [ ] Avatar-Gradient und Violet/Indigo-Aktionsfarben entfernen.
- [ ] Destruktive Bestätigungen als Cockpit-Dialog statt Browser-`confirm` umsetzen.
- [ ] Guard, TypeScript, Scope-ESLint, Build und visuellen Browser-Test ausführen.
- [ ] Eigener PR; Etappe-2-Task abschließen.

### Task 8: Containers

- [ ] Guard zunächst ROT gegen Containers-Erreichbarkeitsbaum ausführen.
- [ ] Cards, Summary, Details, Console und Dialoge migrieren.
- [ ] Detailansicht als gestapeltes Overlay öffnen; Task `54cbbc74` integrieren.
- [ ] Guard, TypeScript, Scope-ESLint, Build und visuellen Browser-Test ausführen.
- [ ] Eigener PR; Etappe-3-Task abschließen.

### Task 9: Gesamtaudit

- [ ] Alle AdminOverlay-Einstiege und transitiv erreichbaren Komponenten inventarisieren.
- [ ] Statischen Guard auf vollständig migrierte Admin-Scopes erweitern.
- [ ] LLM-Catalog-Follow-up `6dc1b158`, Skills und verbleibende Doppelverknüpfungen bewerten/einordnen.
- [ ] Alle Funde migrieren, visuell prüfen und in einem Abschlussbericht dokumentieren.
- [ ] Eigener PR; Umbrella-Task und Etappe-4-Task abschließen.

## Verifikation

Da das Frontend derzeit kein eigenes Vitest/Jest-Setup besitzt, wird für diese reine Styling-/Komponentenarbeit der ausführbare Node-Guard als Regressionstest verwendet. Zusätzlich gelten:

```bash
cd frontend
npm run check:admin-visual
npm run check:cockpit-offline
npx tsc --noEmit
npx eslint <geänderte Dateien>
npm run build
```

Der Browser-Test ist verpflichtend, weil statische Checks keine visuelle Hierarchie, Responsivität oder Stacking-Probleme erkennen.

## Akzeptanzkriterien

- [ ] Spec `docs/specs/admin-cockpit-visual-system.md` ist umgesetzt.
- [ ] System inklusive aller sichtbaren Cards, Settings und Voice ist eine vollständig konsistente Referenz.
- [ ] Users und Containers folgen demselben System.
- [ ] Der Abschlussguard verhindert die Rückkehr der bekannten Legacy-Muster.
- [ ] Keine unnötige Legacy-Navigation bleibt aus dem Admin-Cockpit erreichbar.
- [ ] Keine bestehende Funktion oder API-Interaktion geht verloren.

## Nicht in diesem Plan

- Backend-Änderungen.
- Neue Admin-Funktionen.
- Vollständiges Redesign aller Legacy-Routen außerhalb des Admin-Cockpits.
- Änderung der fachlichen Informationsarchitektur.
