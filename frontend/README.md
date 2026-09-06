# HydraHive frontend

React 19 + TypeScript single-page application for HydraHive. Vite handles development and production builds; the Linux installer serves `dist/` through nginx.

## Stack

- React 19
- React Router 7
- TypeScript 6
- Vite 8
- Zustand
- i18next
- Tailwind CSS utilities plus project CSS/theme variables
- Monaco, xterm, noVNC, D3/Three.js, XYFlow and Recharts in feature-specific bundles

Versions above come from the current `package.json` and change with dependency updates.

## Development

Start the backend first on `127.0.0.1:8001`, then:

```bash
cd frontend
npm ci
npm run dev
```

The Vite dev server proxies:

- `/api` to `http://127.0.0.1:8001` with WebSocket support;
- `/vnc-ws` to `ws://127.0.0.1:6080`.

The repository-level `./dev-start.sh` starts backend and frontend together.

## Checks

```bash
npm run build                  # generates assets/modules/themes, TypeScript build, Vite bundle
npx tsc --noEmit               # standalone type check used by CI
npm run lint                   # ESLint
npm run check:cockpit-offline  # cockpit offline-first guard
npm run check:admin-visual     # admin visual-system guard
npm run preview                # preview production build
```

`npm run build` executes the `prebuild` script first. Do not hand-edit generated files.

## Source layout

```text
src/
├── App.tsx                    # authenticated route tree and core/module routes
├── features/                  # core feature slices (UI + local API adapter)
├── modules/                   # build copies of installed user modules
├── shared/                    # API client, navigation, layout and shared UI
├── themes/                    # bundled theme packages
├── i18n/                      # translation resources and help content
└── assets/                    # static source assets

scripts/
├── gen-emotes.mjs             # generated Hydra emote registry
├── gen-modules.mjs            # module imports/routes/navigation/contributions
└── gen-themes.mjs             # generated theme registry
```

Most core screens live under `src/features/<feature>/` with their own components, API wrapper and state. User modules live under `src/modules/<id>/` and export contributions consumed by `index.generated.ts`.

## Routing and navigation

Core authenticated routes are defined in `src/App.tsx`. Navigation metadata is in `src/shared/nav-config.ts`.

The main cockpit routes are:

- `/projects`
- `/buddy`
- `/media`
- `/vault`
- `/admin` (administrator only)

Legacy/detail feature routes remain available through the app/settings menus. Installed modules contribute routes and navigation dynamically at build time.

A new core route usually requires:

1. a feature page under `src/features/`;
2. a route in `App.tsx`;
3. navigation metadata when it should be discoverable;
4. German and English strings;
5. an appropriate auth/admin guard;
6. help content or an update to the user documentation.

## Module frontend contract

Each module build copy needs an `index.tsx` exporting at least:

```ts
export const routes = []
export const nav = []
export const i18n = { de: {}, en: {} }
```

Optional exports currently collected by the generator are:

- `buddyWidgets`
- `workspaceTabs`
- `slotBlocks`
- `mediaSources`
- `mediaWorkflows`

`npm run build` scans `src/modules`, validates local imports and regenerates `src/modules/index.generated.ts`. If an installed module has a missing local import, the generator removes only its rebuildable frontend copy so the entire HydraHive UI can still build; runtime backend data is not deleted by that step.

The canonical distributable module source lives in the separate `hydrahive2-modules` hub. The backend module installer copies a module's frontend into this directory and then rebuilds the app.

## API client

Use `src/shared/api-client.ts` rather than duplicating fetch/auth handling. Feature-local adapters should expose typed operations, for example `src/features/agents/api.ts` or `src/modules/tasks/api.ts`.

Conventions:

- feature adapters use paths relative to `/api` through the shared client;
- abortable streams and raw file responses may use specialized helpers;
- never log or render secret values returned during setup flows;
- map coded backend errors to localized user-facing messages.

## Cockpit architecture

The cockpit pages use a dedicated, theme-independent shell for dense operational workflows. Shared pieces are under `src/features/cockpit/`:

- `CockpitShell`, `CockpitTopbar` and panel/button primitives;
- project overlays for files, Git, agents, access, servers, mounts and graph;
- media workspace, prompt, screenplay, assets and timeline/cut views;
- Vault privacy/data launchpad;
- admin overlays for users, models, credentials, modules, extensions, plugins, VMs, containers, nodes and system.

Cockpit actions should remain local/offline-first unless the user explicitly enters an AI chat or starts a generation action. Guard scripts enforce key parts of this design.

## Themes

Themes can provide:

- CSS variables;
- optional raw CSS;
- a layout component/chrome;
- themed route fallbacks.

The active theme is stored in the browser and applied by `src/shared/Layout.tsx`. Core cockpit routes intentionally use their own bare cockpit chrome. Run `npm run gen:themes` or a full build after adding a bundled theme.

## Internationalization

Use the existing i18next namespaces under `src/i18n`. User-visible features should provide German and English strings. Module translations are merged from each module's `i18n` export.

Avoid hard-coded text in reusable components where a translation namespace already exists. Point-in-time prototypes may contain German labels, but production changes should preserve both supported languages.

## Production build and caching

```bash
npm run build
```

Output is written to `frontend/dist/`. Vite emits content-hashed assets and source maps. The generated nginx configuration:

- caches `/assets/` as immutable;
- revalidates HTML to avoid a stale `index.html` referencing removed hashes;
- serves unknown frontend routes through `index.html`;
- proxies `/api` and WebSocket paths to the backend.

## Contribution rules

- Follow the repository size/co-location conventions in `../CONTRIBUTING.md`.
- Do not edit `index.generated.ts`, generated emote lists or generated theme registries manually.
- Keep admin-only routes behind `AdminGuard` or equivalent server-backed authorization.
- Frontend guards improve UX; the backend must still enforce every permission.
- Run `npx tsc --noEmit` and `npm run build` before declaring a frontend change complete.
