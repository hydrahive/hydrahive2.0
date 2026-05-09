# Architektur-Dokumentation

> Subsystem-Deep-Dives. Nicht-normativ — Quelle der Wahrheit ist immer der
> Code. Ziel: Onboarding für neue Contributor / KI-Sessions ohne dass sie
> sich durch 343 .py-Files lesen müssen bevor sie was beitragen können.

## Subsysteme

| Doc | Was |
|---|---|
| [memory.md](memory.md) | Memory v2 Pipeline — Observation → Compress → Crystallize → Lessons → Context-Injection |
| [runner.md](runner.md) | Tool-Loop, Streaming vs Fallback, Provider-Switch, Token-Counts |
| [compaction.md](compaction.md) | Append-only `firstKeptEntryId`-Pointer, hierarchisches Merging, Live-Truncation |
| [auth.md](auth.md) | JWT, API-Keys, Roles, Login-Lockout, OAuth-Flow + atomic Refresh |

## Pflege-Hinweise

- Docs werden **nicht** automatisch aus Code generiert — bei größeren
  Refactorings die betroffene Doc kurz prüfen
- Kein Code-Snippet-Copy außer als Beispiel — sonst veraltet er ungesehen
- File-Refs (`runner/_call.py`) sind robust gegen Line-Drift, aber Line-Refs
  (`:42`) altern schnell. Bei Letzterem im Kommit-Trailer dokumentieren wenn
  bewegt
- Bei neuer/entfernter Subsystem-Datei: Tabelle hier + STRUCTURE.md anpassen
