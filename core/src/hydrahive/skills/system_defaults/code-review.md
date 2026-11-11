---
name: code-review
description: Strukturierter Code-Review mit fokussierter Reihenfolge
when_to_use: Wenn der User um ein Code-Review oder Bug-Suche bittet
tools_required: [file_read, shell_exec]
---

Beim Code-Review checkst du in dieser Reihenfolge:

1. **Korrektheit** — tut der Code was er soll? Off-by-One, Edge Cases, Race Conditions, Null/Undefined
2. **Sicherheit** — Input-Validation, Injection (SQL, Command, Path Traversal), Auth-Checks, Secret-Leaks
3. **Fehlerbehandlung** — werden Errors geschluckt? Sind Boundary-Errors klar (Logging mit Kontext)?
4. **Klarheit** — Funktions-Namen, Variablennamen, Schichten-Trennung. Code soll selbsterklärend sein
5. **Konsistenz** — passt der Stil zum Rest der Codebase? SPEC.md / Style-Guides befolgt?
6. **Tests** — sind die kritischen Pfade abgedeckt? Edge Cases?
7. **Performance** — N+1, unnötige Schleifen, große Allocations — nur wenn relevant

Was du **NICHT** machst:
- Kommentar-Spam pro Zeile mit "looks good"
- Bikeshedding (Tabs vs Spaces, ob ein `let` ein `const` sein soll wenn's nichts ändert)
- Refactor-Vorschläge die den Scope sprengen — als separates Issue empfehlen

Format der Antwort: nach Prioritätskategorien (Blocker / Wichtig / Nice-to-have).

## Jeder Fund wird ein Test

Für jeden Blocker und jeden wichtigen Fund nennst du den **Test, der ihn festhält**: Was wird geprüft, und warum
ist der Test ohne den Fix rot? So kommt dieselbe Fehlerart nicht unbemerkt wieder. Lässt sich ein Fund nicht
automatisch prüfen (z. B. nur auf echter Hardware), sag das ausdrücklich und nenne den Grund. Er gehört dann als
„Kein Test: <Begründung>“ in die PR-Beschreibung (Regel: docs/specs/fix-test-guard.md).
