# Deep-Dive-Audit: Legacy-Design vs. Cockpit-Shell

- Datum: 2026-07-15
- Basis-Commit (live): `c98592b7`
- Auslöser: Projekt-Cockpit → Auswerten → Sessions öffnet den **alten Werkstatt-Chat** statt einer Cockpit-Ansicht.

## Kriterium (aus Handover übernommen)
Entscheidend ist das **Layout-Gerüst**, nicht einzelne Utility-Klassen:
- **Cockpit-Shell** = Route liegt in `cockpitPaths` (`Layout.tsx:37`: `/projects`, `/buddy`, `/media`, `/vault`, `/admin`) → bare Chrome `bg-[#080b11]` + `CockpitTopbar`/`CockpitShell`.
- **Legacy** = alles andere läuft unter `ActiveLayout` (Theme-Sidebar/Topnav) und/oder nutzt `className="box"` (altes Design-Gerüst).
- `zinc-`/`slate-`-Klassen allein sind **kein** Legacy-Indikator (Teil des aktuellen Dark-Designs).

## Architektur-Fakten
- Routing zentral in `frontend/src/App.tsx`. Nur 5 Routen sind Cockpit; alle anderen laufen über `ActiveLayout` (viele mit `ThemedPage`-Fallback).
- Cockpit-Ausgänge nutzen zwei Muster, die **immer** in Legacy-Seiten führen:
  - `openLocalPath(path)` = `window.open(path, "_self")` (`actionRegistry.ts:11`) → Vollreload in Legacy-Route.
  - `go(path)` = `window.open(path, "_self")` (`CockpitTopbar.tsx:25`) → dito.
- `SessionDetailPage` (`/analytics/session/:sid`) existiert als moderner Detail-View, wird aus dem Cockpit aber **nicht** verlinkt und zeigt selbst zurück ins Legacy (`/dashboard`, `/werkstatt?session=`).

---

## Findings (priorisiert)

### P0 — Sessions öffnen die Legacy-Werkstatt (der gemeldete Bug)
| Feld | Wert |
|------|------|
| Datei:Zeile | `features/projects/_SessionsTab.tsx:41` |
| Code | `onClick={() => navigate(\`/werkstatt/${s.id}\`)}` |
| Aufrufkette | `ProjectActionGroups.tsx:34` (Button „Sessions") → `ProjectInsightsOverlay.tsx:48` (rendert `SessionsTab`) → `_SessionsTab.tsx:41` |
| Ursache | Harte Navigation in die Legacy-Route `/werkstatt/:sid` (ChatPage unter `ActiveLayout`). Verlässt das Cockpit komplett. Die Overlay-Footer-Copy (`ProjectInsightsOverlay.tsx:19`) beschreibt das sogar als gewolltes Verhalten. |
| Migrationsvorschlag | Ziel-Route auf den Cockpit-tauglichen Detail-View umstellen: `navigate(\`/analytics/session/${s.id}\`)` **oder** — sauberer — Session-Detail als Overlay/Tab **innerhalb** des Cockpits rendern (kein Route-Wechsel). Dazu `SessionDetailPage` von den `box`/`/dashboard`-Rücklinks entkoppeln (siehe P1-A). |

### P1-A — SessionDetailPage hängt selbst im Legacy
| Feld | Wert |
|------|------|
| Datei:Zeile | `features/analytics/SessionDetailPage.tsx:32` (`<Link to="/dashboard">`), `:42` (`<Link to="/werkstatt?session=…">`), `:109` (`className="box"`) |
| Ursache | Route `/analytics/session/:sid` läuft unter `ActiveLayout`; Rücksprünge zielen auf Legacy-Seiten; Sektionen nutzen `box`. Damit ist sie als P0-Ziel nur bedingt geeignet. |
| Migrationsvorschlag | Entweder in eine Cockpit-Route heben (in `cockpitPaths` aufnehmen + `CockpitTopbar`) oder als eingebettete Detailansicht im Projekt-Cockpit-Overlay verwenden. Rücklinks auf Cockpit-Ziele (`/projects`) umbiegen; `box` → Cockpit-Panels. |

### P1-B — Cockpit-Ausgänge führen systematisch in Legacy-Seiten
| Fundstelle | Ziel(e) | Landet in |
|------------|---------|-----------|
| `CockpitTopbar.tsx:22,25` | `/help` | Legacy `HelpPage` (`box`) |
| `actionRegistry.ts` (Vault) | `/akte`, `/cryptoboard`, `/scratchpad`, `/credentials` | Legacy/Module |
| `actionRegistry.ts` (Admin) | `/system`, `/users`, `/modules`, `/extensions`, `/plugins`, `/credentials` | Legacy (alle `box`) |
| `actionRegistry.ts` (Media) | `/atelier`, `/streaming`, `/musicplayer`, `/videoeditor` | Legacy/Module |
| `MediaAssetOverlay.tsx:25,26` | `/atelier`, `/music` | Legacy/Module |
| `BuddyPage.tsx:176-177` | `/scratchpad`, `/musicplayer`, `/minigames`, `/boardgames` | Module (kein Cockpit-Chrome) |
| Ursache | `openLocalPath`/`go` machen `window.open(_self)` → harter Reload in Nicht-Cockpit-Route. Für viele Ziele existiert (noch) keine Cockpit-Variante. |
| Migrationsvorschlag | Zwei Stufen: (1) kurzfristig konsistent lassen, aber dokumentieren welche Ziele bewusst Legacy sind; (2) mittelfristig je Ziel entscheiden: in Cockpit-Overlay ziehen (z. B. Credentials, System-Status) vs. bewusst Legacy-Vollseite. |

### P2-A — Explizite Legacy-Rücklinks im Cockpit-Kontext
| Datei:Zeile | Code | Migrationsvorschlag |
|-------------|------|---------------------|
| `features/cockpit/CockpitPlaceholderPage.tsx:44` | `<Link to="/werkstatt">Alte Werkstatt öffnen</Link>` | Entfernen, sobald Cockpit-Chat verfügbar ist; bis dahin als „Legacy" kennzeichnen. |
| `App.tsx:89` | `/devchat → /werkstatt` | OK als Alias; nach Cockpit-Chat auf neue Route umbiegen. |
| `features/dashboard/_TokenAuditCard.tsx` | Link auf `/analytics/session/:id` | Bereits die „bessere" Route — konsistent halten. |

### P2-B — Legacy-Seiten-Inventar (Design-Schuld, `className="box"`)
~100 Komponenten in ~35 Feature-Ordnern nutzen noch `box`. Kern-Seiten (unter `ActiveLayout`): `SystemPage`, `SettingsPage`, `CommunicationPage`, `Containers*`, `CredentialsPage`, `Extensions*`, `FederationPage`, `HelpPage`, `CatalogPage`, `ProfilePage`, `SkillsPage`, `VMsPage`, `ZahnfeePage`, `SessionDetailPage`. → Reine Redesign-Schuld, **nicht** teil des P0-Bugs. Sinnvoll als eigener, gestaffelter Redesign-Track pro Bereich.

---

## Empfohlene Reihenfolge
1. **P0** zuerst isoliert fixen (kleiner, klar testbarer Change): Sessions-Klick nicht mehr nach `/werkstatt/:sid`.
2. **P1-A** direkt danach, weil P0 sauber nur funktioniert, wenn das Ziel (`SessionDetailPage` oder Overlay) selbst cockpit-tauglich ist.
3. **P1-B** als Policy-Entscheid mit Till (welche Ausgänge bleiben bewusst Legacy?).
4. **P2** als separater Redesign-Track, bereichsweise.

## Offene Design-Frage an Till (blockiert sauberen P0-Fix)
Soll die Session aus dem Cockpit …
- (A) im **modernen Detail-View** `/analytics/session/:sid` geöffnet werden (Analytics, read-only), **oder**
- (B) als **echter Chat** weiterlaufen — dann braucht es einen Cockpit-Chat (existiert noch nicht; heute nur Legacy-Werkstatt), **oder**
- (C) als **Overlay/Tab im Projekt-Cockpit** eingebettet (kein Route-Wechsel)?
