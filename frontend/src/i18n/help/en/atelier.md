# Atelier — create images, videos, audio and whole films

## What is this?

The **Atelier** is your media workshop. Here you have AI generate **images**,
**videos**, **music/speech**, and even **whole short films** — all bound to a
**project** so your works stay cleanly separated. The special part: through
**characters** and a **style anchor**, the look stays **consistent** across many
images (the same figure always looks the same).

At the top you pick the **project** you're working in. All generated media land in
its storage.

## The tabs

### Generate
The starting point: you describe via a **prompt** what should be created, pick a
**model** and format, and generate an image. If you select a **character**, its
profile is automatically merged into the prompt — so it stays recognizable.

### Gallery
All generated **images** of the project. From here you can view images, reuse them
(as reference/start frame for videos), or delete them. A picture's exact prompt is
also viewable and copyable.

### Videos
From a prompt — or from an existing image as a **start frame** — short **video
clips** are created. Each model offers different **durations** and **formats** (the
selection adapts automatically to the chosen model so no invalid combination
occurs). Each clip shows model, duration, format, and source as small info badges.

### Audio
Generates **music** or **speech** (voiceover) — useful for scoring films.

### Director (screenplay → film)
The most ambitious part: you write a **screenplay** (title, logline, description),
and a **director agent** breaks it into **scenes** and **shots** (individual camera
setups). For each shot you can generate image and video, step by step to the
finished film. Camera setups (close-up, wide, aerial …) help steer the look
deliberately.

## Characters & style — the key to consistency

- **Character (figure)** — has a **profile** (appearance, traits) that is merged
  **verbatim into every prompt**, plus optionally a **style anchor**, **palette**
  (hex colors), and **seed**. This way the same figure looks the same in every
  image.
- **Style anchor** — a fixed style block (e.g. *"flat vector, thick outlines"*) that
  stays constant across an image series.
- **Reference images** — uploaded templates the generation orients itself to.

## Step by step: from image to film

1. Pick a **project** at the top (or create one first).
2. Optionally create a figure under **Characters** with profile + style anchor.
3. **Generate** tab: write a prompt, pick figure/model/format → generate image.
4. **Videos** tab: create a clip from the image (start frame) or a prompt —
   duration/format per model.
5. **Audio** tab: generate matching music or a voiceover.
6. **Edit film**: click several clips in order and **render** (mixed formats are
   fitted in), optionally add music.
7. For structured projects: **Director** tab — write a screenplay, have the
   director agent break it into scenes/shots, and work through it.

## Common mistakes

- **"No projects available"** — The Atelier is project-bound. First create one
  under *Projects*.
- **Video fails / format rejected** — Use the **durations/formats** offered by the
  model; the selection is already tailored to the model.
- **Figure looks inconsistent** — Profile too vague. Describe appearance concretely
  and use **style anchor** + **seed** for repeatability.
- **Film tab empty** — Generate **videos** first; the film assembles existing clips.

## Tips

- **Character first, then the series**: a good character profile saves a lot of
  later touch-up.
- **Use an image as a start frame** for videos best from the **Gallery** — that
  preserves the look.
- **Reuse prompts**: via the prompt view you can copy successful prompts and reuse
  them slightly modified.
- **Director for longer stories**: instead of juggling clips individually, the
  screenplay approach gives you structure (scenes → shots) and a through-line.
