# Feature-Spec: Prompt-Archiv (Prompt Library)

> **Status:** Entwurf — wartet auf Freigabe
> **Erstellt:** 2026-06-25
> **Autor:** Hopper (Buddy) für till
> **Ziel:** Wertvolle Generierungs-Prompts (Bild/Musik/System/…) speichern, kategorisieren, per Klick in den Chat holen — und programmatisch durch den Agenten nutzbar machen.

---

## 1. Problem

KI-Prompts sind ein wertvolles Asset geworden. Heute gehen sie nach jeder Session verloren. Besonders schmerzhaft bei **Serien**: ein zweites Bild im gleichen Look oder ein stimmiges Musik-Album ist ohne den exakten Original-Prompt (+ Modell + Seed + Parameter) praktisch nicht reproduzierbar.

Es fehlt ein persistenter, durchsuchbarer Speicher für Prompts — erreichbar von **zwei Seiten**:
1. **User** klickt einen gespeicherten Prompt im Chat-Footer an → landet im Eingabefeld → anpassen → abschicken.
2. **Agent** greift programmatisch zu → holt passenden Prompt, passt ihn an, generiert direkt ("mach noch ein HydraHive-Bild").

## 2. Scope

**Volles Programm** (bewusste Entscheidung). Ein Eintrag ist nicht nur Text, sondern ein vollständiges **Rezept**.

### In Scope
- Per-User Prompt-Speicher mit Kategorien
- Volles Rezept: Titel, Kategorie, Prompt-Text, Modell, Parameter (JSON), Seed, optionales Beispiel-Medium, Tags, Notizen
- **Public-Toggle** pro Eintrag — Standard privat, einzeln teilbar
- Chat-Footer-Picker (Overlay analog `EmotePicker`) → Prompt in Input
- Agent-Tools: Prompts auflisten/suchen + lesen
- Suche & Filter nach Kategorie/Tags/Volltext

### Explizit NICHT in Scope (erste Version)
- Kein Teilen einzelner Prompts an *bestimmte* User (nur privat ⇄ public global)
- Keine Versionshistorie pro Eintrag (nur `updated_at`); "v2"-Varianten legt man als neuen Eintrag an
- Kein automatisches Zurückschreiben des Seeds aus einer Generierung (später; siehe Ausblick)
- Kein Import/Export (später)

## 3. Bestehende Patterns (wiederverwenden)

| Was | Vorlage im Repo |
|---|---|
| Footer-Picker (Button + Overlay-Popover, Klick → Input) | `frontend/src/features/chat/EmotePicker.tsx` |
| DB-Modul (CRUD, `with db() as conn`, upsert) | `core/src/hydrahive/db/teamchat.py` |
| Migration (SQL-Datei, nummeriert) | `core/src/hydrahive/db/migrations/025_teamchat.sql` → nächste freie: **029** |
| API-Route + Registrierung | `core/src/hydrahive/api/routes/teamchat.py` + `api/main.py` (`include_router`) |
| Agent-Tool (Schema + run) | `core/src/hydrahive/tools/generate_image.py`, `read_memory.py` |
| Generierungs-Parameter (Modell/width/height/seed) | `generate_image.py`, `generate_music.py` |

## 4. Datenmodell

Tabelle `prompt_archive` (Migration `029_prompt_archive.sql`):

| Spalte | Typ | Bedeutung |
|---|---|---|
| `id` | TEXT PK | UUID |
| `user_id` | TEXT NOT NULL | Besitzer |
| `title` | TEXT NOT NULL | Anzeigename ("HydraHive Maskottchen") |
| `category` | TEXT NOT NULL | `image` \| `music` \| `system` \| `video` \| `speech` \| `other` |
| `prompt` | TEXT NOT NULL | Der eigentliche Prompt-Text (variabler Teil) |
| `style_anchor` | TEXT | **Konsistenz-Hebel #1.** Fester Stil-Block, der bei jeder Serie gleich bleibt ("oil painting, muted earth tones, dramatic side light"). Wird dem Prompt vorangestellt. |
| `model` | TEXT | z.B. `openai/gpt-5-image-mini` |
| `params` | TEXT (JSON) | `{width, height, transparent, duration, …}` — modellabhängig |
| `seed` | INTEGER | Optional, Zukunfts-Feld. **Hinweis:** GPT-Image/Gemini (autoregressiv) unterstützen Seeds NICHT zuverlässig — Konsistenz läuft über `style_anchor` + `sample_path` (Referenzbild). Seed nur relevant falls später ein Diffusion-Modell/ComfyUI angebunden wird. |
| `tags` | TEXT (JSON-Array) | `["album-neon", "v2"]` |
| `notes` | TEXT | Freitext ("Bass aufgedreht, funktioniert besser") |
| `sample_path` | TEXT | **Konsistenz-Hebel #2.** Pfad zu Beispiel-Bild/-Track im Workspace. Bei Bildserien das Referenzbild für die Fortsetzung (GPT-Image/Gemini können image-to-image). |
| `is_public` | INTEGER (0/1) | Sichtbar für andere User |
| `use_count` | INTEGER | Wie oft in Chat geladen (Sortierung "meistgenutzt") |
| `created_at` | TEXT | ISO |
| `updated_at` | TEXT | ISO |

Indizes: `(user_id, category)`, `(is_public)`.

**Sichtbarkeitsregel:** Ein User sieht eigene Einträge (alle) + fremde mit `is_public=1`. Schreiben/Löschen nur am eigenen Eintrag.

## 5. Backend

### 5.1 DB-Modul `core/src/hydrahive/db/prompt_archive.py`
- `create(user_id, title, category, prompt, **rest) -> dict`
- `get(prompt_id) -> dict | None`
- `list_for_user(user_id, category=None, query=None, include_public=True) -> list[dict]`
- `update(prompt_id, user_id, **fields) -> dict`  (prüft Ownership)
- `delete(prompt_id, user_id) -> bool`  (prüft Ownership)
- `bump_use_count(prompt_id) -> None`

### 5.2 API-Route `core/src/hydrahive/api/routes/prompt_archive.py`
JWT-geschützt, `user_id` aus Token. Registrierung in `api/main.py`.

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/prompts` | Liste (Query: `category`, `q`, `include_public`) |
| POST | `/api/prompts` | Anlegen |
| GET | `/api/prompts/{id}` | Einzeln (Ownership oder public) |
| PATCH | `/api/prompts/{id}` | Ändern (nur Owner) |
| DELETE | `/api/prompts/{id}` | Löschen (nur Owner) |
| POST | `/api/prompts/{id}/use` | `use_count++` (beim Laden in Chat) |

### 5.3 Agent-Tools `core/src/hydrahive/tools/prompt_archive.py`
- `list_prompts(category=None, query=None)` → Titel/Kategorie/ID/Tags (kompakt, kein Volltext-Dump)
- `get_prompt(id)` → volles Rezept
- `save_prompt(title, category, prompt, model=…, params=…, seed=…, tags=…, notes=…)` → neuer Eintrag

So kann der Agent: "mach noch ein HydraHive-Bild" → `list_prompts(category="image", query="hydrahive")` → `get_prompt(id)` → `generate_image(prompt=…, model=…)`. Und: gemeinsam erarbeiteten Prompt mit `save_prompt(...)` ablegen.

## 6. Frontend

### 6.1 Footer-Picker `frontend/src/features/chat/PromptArchivePicker.tsx`
- Neuer Button in der Reihe in `MessageInput.tsx` (📎 · 🎤 · 😀 · **📚** · ▶), Icon z.B. `Library`/`BookMarked` (lucide).
- Klick → Overlay (analog EmotePicker, aber größer — Liste statt Raster).
- Kopf: Kategorie-Tabs (Bild / Musik / System / …) + Suchfeld.
- Liste: Titel + Tags + kleine Vorschau (falls `sample_path`). Zwei Aktionen pro Eintrag:
  - **„In Chat"** → `onPick(prompt)` setzt Text ins Input, `POST /use`.
  - **„Bearbeiten"** → Edit-Dialog.
- „+ Neu" Button → Anlege-Dialog.
- Public-Badge an geteilten Einträgen; Toggle im Edit-Dialog.

### 6.2 API-Client `frontend/src/features/chat/promptArchive.ts` (oder eigenes Feature-Folder)
Thin fetch-Wrapper analog `EmotePicker`-Umfeld.

### 6.3 i18n
DE/EN Strings (das Repo ist zweisprachig).

## 7. Akzeptanzkriterien

- [ ] Migration `029` legt `prompt_archive` an; `apply_migrations` läuft sauber durch.
- [ ] User kann über UI Prompt anlegen, bearbeiten, löschen, als public schalten.
- [ ] Footer-Button öffnet Overlay; Klick auf "In Chat" füllt das Eingabefeld; `use_count` steigt.
- [ ] Kategorie-Tabs + Volltextsuche filtern korrekt.
- [ ] User sieht eigene + public Prompts; fremde private sind unsichtbar; Edit/Delete nur am eigenen.
- [ ] Agent-Tools `list_prompts` / `get_prompt` / `save_prompt` funktionieren end-to-end (Prompt holen → generieren; Prompt speichern).
- [ ] Reproduzierbarkeit: gespeicherter Seed + Modell + Params reichen, um eine Bildserie konsistent fortzusetzen.
- [ ] JWT-Auth auf allen Endpoints; Ownership-Checks bei Schreiboperationen.

## 8. Ausblick (später, nicht jetzt)
- **Referenzbild als Tool-Input:** `generate_image` um optionalen `reference_image_path` erweitern (image-to-image), damit `sample_path` aus dem Archiv direkt als Stil-Referenz in die Folge-Generierung geht. Macht den Serien-Workflow komplett rund. (Bewusst NICHT im Backend-Schritt — eigene Etappe.)
- „Aus letzter Generierung speichern" — Modell/Params automatisch aus dem Tool-Result ins Archiv ziehen (Seed nur falls Modell ihn liefert).
- Teilen an bestimmte User / Teams statt nur global public.
- Import/Export (JSON), Community-Sammlung.
- Falls Diffusion-Backend (ComfyUI/SD) angebunden wird: Seed-Feld wird dann aktiv genutzt.

## 9. Offene Punkte
- (geklärt) Per-User mit Public-Toggle: **ja**
- (geklärt) Volles Rezept statt nur Text: **ja**
- (geklärt) Backend-Modul Option A: **ja**
