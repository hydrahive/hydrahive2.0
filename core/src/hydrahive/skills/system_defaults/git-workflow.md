---
name: git-workflow
description: Saubere Git-Commits + Push-Pattern für Projekt-Arbeit
when_to_use: Wenn du Code änderst der committet werden soll
tools_required: [shell_exec]
---

Vor jedem Commit:

1. **`git status`** — schau was geändert ist. Sind unerwartete Files dabei?
2. **`git diff`** — letzter Sanity-Check vor dem Commit
3. **Staging gezielt** — `git add <file1> <file2>`, nie `git add -A` außer du bist sicher dass alles soll
4. **Commit-Message** im Imperativ, kurz aber spezifisch:
   - `fix(routes/auth): JWT-Token-Verfall um 1h verlängern`
   - `feat(chat): Edit-Resend für User-Bubbles (#43)`
   - **NICHT**: "stuff", "wip", "fix bug"

5. **Push** mit `git push` — wenn Branch tracking nicht gesetzt: `git push -u origin <branch>`

Bei Push-Fehlern:
- `non-fast-forward` → `git pull --rebase` zuerst, dann push
- Auth-Fehler → GH_TOKEN/GITHUB_TOKEN sollte automatisch gesetzt sein wenn das Projekt einen Token hat. Sonst: token im Projekt-Settings prüfen.

**Niemals** `--force` ohne Rückfrage. **Niemals** `--no-verify` (überspringt Hooks).
