---
name: project-management
description: GitHub Issues und PRs verwalten — erstellen, tracken, kommentieren, schließen
when_to_use: Wenn Issues erstellt/geschlossen werden sollen, PRs reviewed werden, oder Milestone-Status geprüft wird
tools_required: [shell_exec]
---

# Projekt-Management

## Issues

```bash
# Übersicht
gh issue list --state open --limit 20

# Issue erstellen
gh issue create --title "Kurzer Titel" --body "Beschreibung" --label "bug"

# Issue schließen (mit Begründung)
gh issue close <nr> --comment "Fixed in <commit>"

# Issue kommentieren
gh issue comment <nr> --body "Kommentar"
```

## Pull Requests

```bash
# PR erstellen
gh pr create --title "Titel" --body "$(cat <<'EOF'
## Was
- Änderung 1
- Änderung 2

## Test
- [ ] Lokal getestet
EOF
)"

# PR-Status
gh pr list
gh pr view <nr>
gh pr review <nr> --approve
gh pr merge <nr> --squash
```

## Milestone-Tracking

```bash
gh issue list --milestone "v2.0" --state open
gh issue list --label "p1" --state open
```

## Reihenfolge bei Feature-Issues

1. Issue lesen und verstehen — was ist Akzeptanzkriterium?
2. Implementieren, testen
3. `gh issue close <nr> --comment "Fixed in <commit>"`
4. Kein Issue schließen ohne dass das Feature wirklich funktioniert
