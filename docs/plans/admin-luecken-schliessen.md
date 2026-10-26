# Plan: Lücken im Admin-Cockpit schließen (Schritt 1 von „ein Zuhause pro Einstellung“)

Task 36bd2884. Till hat am 26.10.2026 freigegeben: Jede Einstellung bekommt genau ein
Zuhause. Der alte Einstellungs-Hub (`/settings`) wird später zu „Meine Einstellungen“.
**Dieser Plan entfernt nichts.** Er sorgt nur dafür, dass das Admin-Cockpit alles kann,
was bisher nur der Hub konnte. Erst dann (Schritt 2, eigener PR) wird der Hub ausgedünnt.

## Ziel

Nach diesem PR gibt es im Admin-Cockpit (`/admin`):

1. **KI-Modelle**: den Abschnitt für Bild- und Video-Dienste (ComfyUI usw.,
   `MediaBackendsSection`). Bisher gibt es ihn nur in `LlmPage` im Hub.
2. **Zugangsdaten**: die Warnung „Zugang ohne Host wird nie eingesetzt“ (Banner mit
   Anzahl, dazu je Karte ein Hinweis). Bisher nur in `CredentialsPage`.
3. **Föderation**: ein eigenes Admin-Fenster `/admin?section=federation` mit dem vollen
   Umfang der `FederationPage` (Workstations, Peers, Clients, Datamining-Instanzen).
   Erreichbar über eine Kachel im Admin-Cockpit und über den Pfad `/federation` in den
   Admin-Links. Weil die Seite lang ist, gliedert sie sich gleich in **Reiter**, nach
   der neuen Regel „Seiten kurz halten“.

Befund aus dem Code-Vergleich (main f4b081c4), deshalb sind es genau diese drei:
- Benutzer, globale Werte und System-Status leiten bereits nach `/admin` weiter.
- Module, Plugins, Themes, MCP, Erweiterungen, Tailscale/AgentLink/Samba/Backup/Bridge
  rufen in Hub und Admin dieselben API-Funktionen auf, es gibt also keinen Verlust.
- Zugangsdaten sind pro Nutzer (`list_credentials(username)`). Sie bleiben deshalb
  später **auch** in „Meine Einstellungen“. Hier geht es nur um die fehlende Warnung.

## Dateien

- `frontend/src/features/credentials/unbound.ts` (neu): `countUnbound(creds)`, eine
  gemeinsame Zählung für Hub und Admin (statt doppeltem Filter).
- `frontend/src/features/credentials/unbound.test.ts` (neu)
- `frontend/src/features/credentials/CredentialsPage.tsx`: nutzt `countUnbound`
- `frontend/src/features/cockpit/admin/CredentialsOverlay.tsx`: Banner und Kartenhinweis
- `frontend/src/features/cockpit/admin/CredentialsOverlay.test.tsx` (neu)
- `frontend/src/features/cockpit/admin/LlmOverlay.tsx`: `<MediaBackendsSection />` unter den Standard-Modellen
- `frontend/src/features/cockpit/admin/LlmOverlay.test.tsx` (neu)
- `frontend/src/features/federation/federationTabs.ts` (neu): Reiterliste und `parseFederationTab()`
- `frontend/src/features/federation/federationTabs.test.ts` (neu)
- `frontend/src/features/federation/WorkstationsPanel.tsx` (neu): Workstation-Liste und
  Hinzufügen-Dialog, herausgelöst aus `FederationPage` (bleibt unter 200 Zeilen)
- `frontend/src/features/federation/FederationPage.tsx`: nutzt `WorkstationsPanel`
  (Verhalten unverändert, die Seite bleibt bis Schritt 2 im Hub)
- `frontend/src/features/cockpit/admin/FederationOverlay.tsx` (neu): AdminOverlay mit
  Reitern „Workstations · Peers · Clients · Datamining“. Der Reiter steht in der URL
  (`&tab=`), wie bei der Vitrine.
- `frontend/src/features/cockpit/admin/FederationOverlay.test.tsx` (neu)
- `frontend/src/features/cockpit/admin/adminOverlayRegistry.ts`: `"federation"` als
  Fenster-ID, `"/federation": "federation"` in `OVERLAY_BY_PATH`
- `frontend/src/features/cockpit/admin/adminOverlayRegistry.test.ts`: Föderations-Fälle
- `frontend/src/features/cockpit/admin/AdminOverlays.tsx`: `FederationOverlay` rendern
- `frontend/src/features/cockpit/AdminCockpitPage.tsx`: Kachel „Föderation“ in `opsLinks`
- `frontend/src/i18n/locales/{de,en}/federation.json`: Reiter-Beschriftungen `tabs.*`

## Implementierungsreihenfolge

### Task 1: Gemeinsame Zählung „Zugänge ohne Host“
- [ ] Test `unbound.test.ts`: `countUnbound([])` ist 0. Nur `host_bound === false`
      zählt; `true` und `undefined` (alte Einträge ohne Feld) zählen nicht.
- [ ] RED (Datei fehlt)
- [ ] `unbound.ts` mit `countUnbound`; `CredentialsPage` nutzt sie (Zeile 33)
- [ ] GREEN; Mutantenprobe: `!== true` statt `=== false` muss den undefined-Fall rot machen

### Task 2: Warnung im Admin-Fenster Zugangsdaten
- [ ] Test `CredentialsOverlay.test.tsx` (`renderToStaticMarkup`, `credentialsApi` und
      i18n gemockt wie in `PluginCockpitCards.test.tsx`). Weil `useEffect` serverseitig
      nicht läuft, wird die Darstellung als reine Teilkomponente getestet:
      `UnboundBanner({ count })` und `CredentialCard` (bzw. die Karte als eigene Komponente
      `CredentialCockpitCard`):
  - count 0 → rendert nichts
  - count 2 → enthält `unbound_banner:{"count":2}`
  - Karte mit `host_bound:false` → enthält `not_host_bound`; mit `true` → nicht
- [ ] RED
- [ ] `CredentialsOverlay.tsx`: Karte als `CredentialCockpitCard` herauslösen, Banner im
      HTTP-Reiter unter `security_note`
- [ ] GREEN; Mutantenprobe: Bedingung `host_bound === false` entfernen → Test rot

### Task 3: Bild-/Video-Dienste im Admin-Fenster KI-Modelle
- [ ] Test `LlmOverlay.test.tsx`: `LlmOverlay` rendern, `MediaBackendsSection` per
      `vi.mock` durch einen Marker `<div data-testid="media-backends"/>` ersetzen,
      `AdminOverlay`, `llmApi` und i18n mocken → Markup enthält `media-backends`
- [ ] RED
- [ ] `LlmOverlay.tsx`: Import und `<MediaBackendsSection />` nach `DefaultModelsSection`
- [ ] GREEN; Mutantenprobe: Zeile entfernen → rot

### Task 4: Reiter-Logik Föderation
- [ ] Test `federationTabs.test.ts`:
  - `FEDERATION_TABS` ist `["workstations","peers","clients","datamining"]`
  - `parseFederationTab(null)` → `"workstations"`; `"peers"` → `"peers"`;
    `"quatsch"` → `"workstations"`
- [ ] RED → `federationTabs.ts` → GREEN; Mutantenprobe: Fallback ändern → rot

### Task 5: Workstation-Teil herauslösen (reine Umstrukturierung)
- [ ] `WorkstationsPanel.tsx` enthält den bisherigen Block aus `FederationPage`:
      Laden, Info-Box, Liste, Leer-Zustand, Hinzufügen-Dialog und eigenen
      „Hinzufügen“-Knopf als Prop-Slot. `FederationPage` rendert Kopf, `WorkstationsPanel`
      und die drei Abschnitte wie bisher.
- [ ] Bestehende Tests (`_tailnetUrl`, `_TailnetUrlWarning`) bleiben grün; `tsc`; die
      Hub-Seite sieht unverändert aus (wird auf der GUI-Reise mit geprüft)

### Task 6: Admin-Fenster Föderation
- [ ] Test `FederationOverlay.test.tsx` mit `MemoryRouter initialEntries`, die vier
      Teile als Marker gemockt:
  - ohne `tab` → nur Marker Workstations sichtbar, Reiter `workstations` `aria-selected="true"`
  - `?section=federation&tab=clients` → nur Marker Clients
  - vier Elemente `role="tab"`
- [ ] Test `adminOverlayRegistry.test.ts`: `isAdminOverlayId("federation")` ist true,
      `OVERLAY_BY_PATH["/federation"]` ist `"federation"`
- [ ] RED
- [ ] Registry, `FederationOverlay.tsx` (Reiter mit `role="tablist"`, Stil wie
      `ProjectMobileTabs`; Reiterwechsel setzt `tab` per `setSearchParams(…, {replace:true})`,
      `section` bleibt), `AdminOverlays.tsx`, Kachel in `AdminCockpitPage.opsLinks`
      (Icon `Globe`), i18n `tabs.workstations|peers|clients|datamining` in de und en
- [ ] GREEN; Mutantenproben: Fallback in `parseFederationTab`, Pfad in `OVERLAY_BY_PATH`
- [ ] Hinweis: `useAdminOverlayNavigation.setOverlay` löscht nur `container`. Beim
      Schließen muss auch `tab` weg, sonst hängt beim nächsten Fenster ein falscher
      Reiter in der URL. Test dafür in Task 6 aufnehmen: `setOverlay(null)` entfernt `tab`.

### Task 7: Prüfen und PR
- [ ] `npx tsc --noEmit`, `npx eslint` (geänderte Dateien), `npx vitest run` (komplett)
- [ ] Dateigrößen ≤ 200 Zeilen (`AdminCockpitPage` liegt bei 181 → nur eine Zeile dazu)
- [ ] Kern-Suite Python ist nicht betroffen (nur Frontend); ruff entfällt
- [ ] Build (`npm run build`), Deploy auf den Testserver
- [ ] **GUI-Reise mit Till** (siehe unten)
- [ ] PR „Admin-Cockpit: Lücken zum Einstellungs-Hub schließen“; Merge nach grüner CI

## GUI-Reise (mit Till, im Browser)

1. `/admin` → Kachel **KI-Modelle** → ganz unten der Abschnitt „Bild- und Video-Dienste“;
   einen Dienst testen bzw. speichern.
2. `/admin` → **Credentials** → bei einem Zugang ohne Host: gelbes Banner oben, Hinweis
   auf der Karte. Nach dem Eintragen des Hosts sind beide weg.
3. `/admin` → Kachel **Föderation** → vier Reiter; jeden anklicken; Seite neu laden, der
   Reiter bleibt (URL). Schließen und ein anderes Fenster öffnen: kein `tab=` in der URL.
4. Hub `/settings/federation` sieht unverändert aus (Gegenprobe Task 5).
5. Als Nicht-Admin-Nutzer: `/admin` bleibt gesperrt (AdminGuard), nichts Neues sichtbar.

## Akzeptanzkriterien

- [ ] Alles, was der Hub für Admins kann, kann auch das Admin-Cockpit
- [ ] Hub und alte Routen funktionieren unverändert (nichts entfernt)
- [ ] Neue und geänderte Dateien ≤ 200 Zeilen
- [ ] Alle Frontend-Tests, tsc und eslint grün; die neuen Tests waren vorher rot
- [ ] GUI-Reise von Till abgenommen

## Nicht in diesem Plan

- Hub ausdünnen und in „Meine Einstellungen“ umbenennen, Eintrag unter „Verwaltung“
  entfernen, Benutzermenü anpassen → **Schritt 2**, eigener PR
- Reiter für System, Module, User, Archiv, Dashboard → **Schritt 3 ff.**
- Optisches Angleichen der `MediaBackendsSection` an den Cockpit-Look (zinc → #2a364b).
  Sie wird unverändert eingebettet; der Look kommt beim Kürzen von „KI-Modelle“ mit Reitern.
- Backend: keine Änderung (Rechte für Medien-Dienste und Föderation sind schon admin-geschützt)
