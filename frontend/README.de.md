# HydraHive-Frontend

> 🇬🇧 [English version](README.md)

React 19 + TypeScript Single-Page-Application für HydraHive. Vite handhabt Development- und Production-Builds; der Linux-Installer serviert `dist/` über nginx.

## Stack

- React 19
- React Router 7
- TypeScript 6
- Vite 8
- Zustand
- i18next
- Tailwind-CSS-Utilities plus Projekt-CSS/Theme-Variablen
- Monaco, xterm, noVNC, D3/Three.js, XYFlow und Recharts in Feature-spezifischen Bundles

Versionen oben stammen aus dem aktuellen `package.json` und ändern sich mit Dependency-Updates.

## Entwicklung

Zuerst das Backend auf `127.0.0.1:8001` starten, dann:

```bash
cd frontend
npm ci
npm run dev
```

Der Vite-Dev-Server proxied:

- `/api` nach `http://127.0.0.1:8001` mit WebSocket-Support;
- `/vnc-ws` nach `ws://127.0.0.1:6080`.

Das Repository-Level-`./dev-start.sh` startet Backend und Frontend zusammen.

## Checks

```bash
npm run build                  # generiert Assets/Module/Themes, TypeScript-Build, Vite-Bundle
npx tsc --noEmit               # eigenständiger Type-Check, von CI genutzt
npm run lint                   # ESLint
npm run check:cockpit-offline  # Cockpit-Offline-First-Guard
npm run check:admin-visual     # Admin-Visual-System-Guard
npm run preview                # Preview des Production-Builds
```

`npm run build` führt zuerst das `prebuild`-Skript aus. Generierte Dateien nicht manuell editieren.

## Source-Layout

```text
src/
├── App.tsx                    # authentifizierter Routen-Tree und Core/Modul-Routen
├── features/                  # Core-Feature-Slices (UI + lokaler API-Adapter)
├── modules/                   # Build-Kopien installierter User-Module
├── shared/                    # API-Client, Navigation, Layout und geteilte UI
├── themes/                    # gebündelte Theme-Pakete
├── i18n/                      # Übersetzungs-Ressourcen und Help-Inhalte
└── assets/                    # statische Source-Assets

scripts/
├── gen-emotes.mjs             # generierte Hydra-Emote-Registry
├── gen-modules.mjs            # Modul-Imports/Routen/Navigation/Contributions
└── gen-themes.mjs             # generierte Theme-Registry
```

Die meisten Core-Screens liegen unter `src/features/<feature>/` mit eigenen Komponenten, API-Wrapper und State. User-Module liegen unter `src/modules/<id>/` und exportieren Contributions, die von `index.generated.ts` konsumiert werden.

## Routing und Navigation

Authentifizierte Core-Routen sind in `src/App.tsx` definiert. Navigation-Metadata liegt in `src/shared/nav-config.ts`.

Die Haupt-Cockpit-Routen sind:

- `/projects`
- `/buddy`
- `/media`
- `/vault`
- `/admin` (nur Administrator)

Legacy/Detail-Feature-Routen bleiben über die App/Settings-Menüs verfügbar. Installierte Module tragen Routen und Navigation dynamisch zur Build-Zeit bei.

Eine neue Core-Route benötigt üblicherweise:

1. eine Feature-Seite unter `src/features/`;
2. eine Route in `App.tsx`;
3. Navigation-Metadata, wenn sie entdeckbar sein soll;
4. deutsche und englische Strings;
5. einen passenden Auth/Admin-Guard;
6. Help-Inhalt oder ein Update der User-Dokumentation.

## Modul-Frontend-Vertrag

Jede Modul-Build-Kopie benötigt ein `index.tsx`, das mindestens exportiert:

```ts
export const routes = []
export const nav = []
export const i18n = { de: {}, en: {} }
```

Optionale Exporte, die der Generator aktuell sammelt:

- `buddyWidgets`
- `workspaceTabs`
- `slotBlocks`
- `mediaSources`
- `mediaWorkflows`

`npm run build` scant `src/modules`, validiert lokale Imports und regeneriert `src/modules/index.generated.ts`. Wenn ein installiertes Modul einen fehlenden lokalen Import hat, entfernt der Generator nur seine rebuild-fähige Frontend-Kopie, damit die gesamte HydraHive-UI trotzdem bauen kann; Runtime-Backend-Daten werden durch diesen Schritt nicht gelöscht.

Die kanonische distributierbare Modul-Source lebt im separaten `hydrahive2-modules`-Hub. Der Backend-Modul-Installer kopiert das Frontend eines Moduls in dieses Verzeichnis und baut die App anschließend neu.

## API-Client

`src/shared/api-client.ts` nutzen statt Fetch/Auth-Handling zu duplizieren. Feature-lokale Adapter sollten typisierte Operationen exponieren, z. B. `src/features/agents/api.ts` oder `src/modules/tasks/api.ts`.

Konventionen:

- Feature-Adapter nutzen Pfade relativ zu `/api` durch den geteilten Client;
- abbrechbare Streams und rohe File-Responses können spezialisierte Helfer nutzen;
- Secret-Werte aus Setup-Flows niemals loggen oder anzeigen;
- codierte Backend-Fehler auf lokalisierte User-Messages mappen.

## Cockpit-Architektur

Die Cockpit-Seiten nutzen eine dedizierte, theme-unabhängige Shell für dichte operationelle Workflows. Geteilte Teile liegen unter `src/features/cockpit/`:

- `CockpitShell`, `CockpitTopbar` und Panel/Button-Primitives;
- Projekt-Overlays für Dateien, Git, Agenten, Zugriff, Server, Mounts und Graph;
- Media-Workspace, Prompt, Drehbuch, Assets und Timeline/Schnitt-Views;
- Vault-Privacy/Data-Launchpad;
- Admin-Overlays für User, Modelle, Credentials, Module, Extensions, Plugins, VMs, Container, Nodes und System.

Cockpit-Actions sollten lokal/offline-first bleiben, außer der Nutzer betritt explizit einen AI-Chat oder startet eine Generierungs-Action. Guard-Skripte erzwingen Schlüsselteile dieses Designs.

## Themes

Themes können bereitstellen:

- CSS-Variablen;
- optionales Raw-CSS;
- eine Layout-Komponente/Chrome;
- themed Routen-Fallbacks.

Das aktive Theme wird im Browser gespeichert und von `src/shared/Layout.tsx` angewendet. Core-Cockpit-Routen nutzen absichtlich ihre eigene bare Cockpit-Chrome. Nach Hinzufügen eines gebündelten Themes `npm run gen:themes` oder einen vollen Build laufen lassen.

## Internationalisierung

Die bestehenden i18next-Namespaces unter `src/i18n` nutzen. Nutzersichtbare Features sollten deutsche und englische Strings liefern. Modul-Übersetzungen werden aus dem `i18n`-Export jedes Moduls gemergt.

In wiederverwendbaren Komponenten keinen hartkodierten Text verwenden, wo bereits ein Übersetzungs-Namespace existiert. Point-in-Time-Prototypen können deutsche Labels enthalten, aber Produktions-Änderungen sollten beide unterstützten Sprachen erhalten.

## Production-Build und Caching

```bash
npm run build
```

Output wird nach `frontend/dist/` geschrieben. Vite emittiert Content-Hashed-Assets und Source-Maps. Die generierte nginx-Konfiguration:

- cached `/assets/` als immutable;
- revalidiert HTML, um ein veraltetes `index.html` mit Verweis auf entfernte Hashes zu vermeiden;
- serviert unbekannte Frontend-Routen über `index.html`;
- proxied `/api` und WebSocket-Pfade zum Backend.

## Beitrags-Regeln

- Den Repository-Size/Co-Location-Konventionen in `../CONTRIBUTING.md` folgen.
- `index.generated.ts`, generierte Emote-Listen oder generierte Theme-Registries nicht manuell editieren.
- Admin-only-Routen hinter `AdminGuard` oder equivalenter serverseitiger Autorisierung halten.
- Frontend-Guards verbessern UX; das Backend muss weiterhin jede Permission erzwingen.
- `npx tsc --noEmit` und `npm run build` laufen lassen, bevor eine Frontend-Änderung als fertig gemeldet wird.
