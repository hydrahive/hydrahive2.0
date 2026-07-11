# Spec: Media-Promptarchiv

## Was

Jedes Media-Projekt erhält ein menschenlesbares, versionierbares Promptarchiv unter `media/<media-slug>/prompts/<type>/<prompt-slug>.md`. Ein Eintrag enthält YAML-Frontmatter für strukturierte Metadaten und einen Markdown-Textkörper für den eigentlichen Prompt.

Unterstützte Typen: `general`, `image`, `video`, `music`, `voice`, `storyboard`. Status: `draft`, `executed`, `archived`.

## Warum

Prompts müssen unabhängig von einer Datenbank, offline und im Samba-/Git-Workspace nachvollziehbar bleiben. Modell, referenzierte Assets, Ergebnisse und Ausführungsstatus dürfen nicht nur in flüchtigem UI-State liegen.

## Wie

- Projektzugriff wird vor jedem API-Zugriff geprüft.
- Typ und Slug werden strikt gegen Allowlist/Regex validiert; aufgelöste Pfade müssen im Promptverzeichnis bleiben.
- Markdown-Dateien werden atomar geschrieben.
- API unterstützt List, Get, Create, Patch und Delete.
- Normales Speichern erzeugt ausschließlich einen Draft und startet keinen LLM- oder Medienjob.
- `executed` dokumentiert nur einen bereits bewusst gestarteten/abgeschlossenen Vorgang samt Ergebnisreferenzen.

## Format

```markdown
---
version: 1
slug: scene-01-keyframe
type: image
title: Szene 01 Keyframe
status: draft
model: openai/gpt-5-image-mini
asset_refs: []
result_refs: []
created_at: 2026-01-01T12:00:00+00:00
updated_at: 2026-01-01T12:00:00+00:00
---

Prompttext
```

## Akzeptanzkriterien

- CRUD funktioniert ausschließlich innerhalb eines zugänglichen Heimatprojekts und existierenden Media-Projekts.
- Traversal, unbekannte Typen/Status und ungültige Slugs werden abgewiesen.
- Dateien bleiben direkt als Markdown lesbar und enthalten vollständige Metadaten.
- Asset- und Ergebnisreferenzen sind reine Workspace-/HydraHive-Referenzen; beim Speichern wird nichts extern geladen.
- Kein Archiv-Endpunkt startet Generierung, LLM oder Rendering.
