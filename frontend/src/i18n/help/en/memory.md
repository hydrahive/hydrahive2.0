# Memory — what your agents remember

## What is this?

Here you see what an agent remembers **beyond individual conversations**. A normal
chat is "forgotten" once closed — memory is where important things persist: notes,
learned facts, and the condensed essence of past sessions.

You pick an **agent** on the right and then see its memory state across three tabs.

## The three tabs

### 1. Memory (notes)

Concrete notes the agent creates itself or that you give it. Each entry has:

- **Key** — the name/keyword the note is filed under (e.g.
  `project.deployment-path`).
- **Content** — the actual note text.
- **Confidence** — how reliable the agent considers this note (0–1). If an entry is
  confirmed repeatedly, confidence rises; contradictory new info can mark old
  entries as outdated.
- **Project** — which project the note belongs to (or global).
- **Updated** — when last changed.

### 2. Crystals

A **crystal** is the automatically condensed essence of a finished session — the
"distillate", so that not every detail but the essentials are preserved. A crystal
typically contains:

- **Key outcomes** — what came out of it.
- **Lessons learned** — what was learned.
- **Affected files** — what was worked on.

This keeps the thread across many sessions without the agent having to drag along
the entire old chat.

### 3. Sessions

The list of this agent's past **sessions** — with the original prompt and the
recorded observations. Useful to trace what happened when.

## Search and filter

- **Search** — searches **key and content** of the entries.
- **Project** — restrict to a specific project (project ID).
- **Show expired** — also show entries that have reached an expiry date (normally
  hidden).

## Step by step: view memories

1. Pick the **agent** on the right.
2. Open the **Memory** tab — the active notes appear.
3. Filter by keyword via **Search**.
4. Unwanted entries can be **deleted** individually.

## Common questions

- **"Why does the agent still know that?"** — Because it's stored as a memory entry
  or crystal. Here you can view it and delete it if needed.
- **"An entry is outdated/wrong"** — Delete it. The agent can create a new, correct
  note when needed.
- **"Where's my old chat?"** — In the **Sessions** tab; the condensed version under
  **Crystals**.

## Tips

- **Read confidence as a hint**: low confidence = the agent is unsure.
- **Use the project filter** if an agent works across several projects — otherwise
  the notes visually mix.
- **Cleanup allowed**: deleting outdated entries keeps the agent focused.
