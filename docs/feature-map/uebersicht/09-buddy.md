# Feature Map: Buddy — Persönlicher Agent pro User

> **Modul:** `core/src/hydrahive/buddy/`  
> **Frontend:** `frontend/src/features/buddy/`  
> **Was:** Der persönliche KI-Begleiter jedes Users. Hat Charakter, Name, Persona.  
> **Warum:** Buddy ist das Herzstück der User-Experience — der "eine" Agent mit dem man täglich spricht.

---

## Backend-Dateien

| Datei | Verantwortung |
|---|---|
| `_config.py` | Buddy-Konfiguration laden/speichern (ist ein Master-Agent mit `is_buddy: true`) |
| `_characters.py` | Vordefinierte Charakter-Templates (z.B. Seven of Nine, Custom, ...) |
| `commands.py` | `/`-Slash-Commands die im Buddy-Chat verfügbar sind |
| `_commands_helpers.py` | Hilfsfunktionen für Command-Parsing und -Ausführung |

---

## Frontend-Dateien

| Datei | Verantwortung |
|---|---|
| `BuddyPage.tsx` | Haupt-Chat-Seite für Buddy. Ähnlich ChatPage, aber Buddy-spezifisch. |
| `_BuddyThread.tsx` | Message-Thread-Ansicht |
| `_BuddyLeftPanel.tsx` | Linke Sidebar: Session-Liste, Suche |
| `BuddySettingsPage.tsx` | Buddy-Einstellungen (Charakter, Modell, Tools, Compaction) |
| `_BuddySettingsIdentity.tsx` | Identitäts-Tab: Name, Charakter, System-Prompt, Soul |
| `_BuddySettingsContext.tsx` | Context-Tab: Compaction-Einstellungen |
| `_BuddySettingsCompaction.tsx` | Compaction-Detail-Einstellungen |
| `_BuddySettingsTools.tsx` | Tools-Tab: welche Tools aktiviert |
| `_BuddyExtensionsPanel.tsx` | Extensions-Panel im Buddy-Chat |
| `_BuddyCmdPill.tsx` | Slash-Command-Autocomplete-Pill im Input |
| `commands.ts` | Frontend: Slash-Command-Definitionen + Rendering |
| `api.ts` | API-Calls für Buddy-Config + Sessions |

---

## Was macht Buddy besonders?

1. **Emote-Hint**: Buddys bekommen einen automatischen Hinweis im System-Prompt
   dass sie Hydra-Emotes (`:hydra-NAME:`) verwenden sollen.
   → `runner/_emote_hint.py` fügt das ein wenn `is_buddy: true`

2. **Charakter-Templates**: Vordefinierte Persönlichkeiten mit fertigen System-Prompts.
   User kann wählen oder eigenen schreiben.

3. **Soul-Dokument**: Optionaler Langzeit-Charakter-Text im `soul/`-Verzeichnis.
   Wird als stabiler Block in den System-Prompt integriert.

4. **Slash-Commands**: `/model gpt-4o`, `/compact`, `/clear`, `/tools`, ...
   Shortcuts für häufige Admin-Aktionen direkt im Chat.

5. **Immer verfügbar**: Buddys haben keinen Projekt-Scope — globaler persönlicher Assistent.

---

## Charakter-Templates (Beispiele aus `_characters.py`)

```python
CHARACTERS = {
    "seven_of_nine": {
        "name": "Seven of Nine",
        "prompt": "Du bist Seven of Nine aus Star Trek...",
        "style": "borg",
    },
    "neutral": {
        "name": "HydraHive Assistant",
        "prompt": "Du bist ein hilfreicher KI-Assistent...",
        "style": "neutral",
    },
    # ...weitere Custom-Charaktere
}
```

---

## Slash-Commands

| Command | Beschreibung |
|---|---|
| `/model <name>` | Aktives Modell für Session wechseln |
| `/compact` | Manuelle Compaction auslösen |
| `/clear` | Session-History löschen (neue Session) |
| `/tools` | Aktive Tools anzeigen |
| `/skills` | Aktive Skills anzeigen |
| `/system` | System-Prompt anzeigen |
| `/debug` | Debug-Infos (Token-Usage, Session-ID) |
| `/effort <low|medium|high>` | Reasoning-Effort setzen |

---

## Buddy vs. normaler Chat-Agent

| Aspekt | Buddy | Chat-Agent |
|---|---|---|
| Typ | Master (is_buddy=true) | Master/Project/Specialist |
| Emotes | ✅ Automatisch | ❌ Nein |
| Slash-Commands | ✅ | ❌ |
| Soul-Dokument | ✅ Optional | ❌ |
| Charakter-Wahl | ✅ | ❌ |
| UI-Tab | "Buddy" | "Chat" |
| Scope | Global (kein Projekt) | Optional Projekt |

---

## Verwandte Subsysteme

- **→ Agents** (`05-agents.md`): Buddy ist ein Master-Agent mit `is_buddy: true`
- **→ Runner** (`01-runner.md`): `_emote_hint.py` im Runner für Emote-Hint
- **→ Chat UI** (`19-frontend-chat.md`): BuddyPage ähnelt ChatPage
- **→ Compaction** (`06-compaction.md`): Buddy hat eigene Compaction-Settings
- **→ Skills** (`11-skills.md`): Buddys können Skills laden
