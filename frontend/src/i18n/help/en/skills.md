# Skills — knowledge and instructions for your agents

## What is this?

A **skill** is a reusable **set of instructions** that an agent loads when needed.
Instead of explaining to an agent every single time *how* to do something ("this
is how you do a code review", "this is how you write a commit message"), you write
it down once as a skill. The agent then pulls in these instructions on its own
when the situation fits.

Think of a skill like a **cheat sheet** or **checklist** sitting on a shelf, to be
opened at the right moment.

## Why is this useful?

- **Consistency**: the agent does a task the same way every time (per your
  guidance), not differently each time.
- **Less repetition**: you don't have to re-explain your approach in every
  conversation.
- **Save context**: the skill is only loaded when actually needed — it doesn't
  weigh the agent down all the time.

## Two kinds of skills

- **Your own skills** — that you create and maintain yourself.
- **System skills** — bundled templates (e.g. for code review, debugging, git
  workflow). These are ready to use.

## A skill's fields

- **Name** — short identifier (only `a-z`, `0-9`, `_`, `-`). **Note:** it **cannot
  be changed** after creation.
- **Description** — what the skill is about (one line).
- **When to use?** — the most important part: one sentence telling the AI **in
  which situation** to load this skill. Example: *"When the user asks for a code
  review."* The clearer, the more reliably the agent reaches for the right skill.
- **Required tools** — comma-separated list of tools the skill assumes (optional).
- **Instructions (Markdown)** — the actual content: the step-by-step guide the
  agent receives on loading.
- **Sources / URLs** — optional addresses (forums, APIs, docs) the agent may fetch
  as part of the skill. If a source needs credentials, provide the name of a
  **credential profile** (see the *Credentials* help) — auth is then injected
  automatically.

## Step by step: create a skill

1. Click **New skill**.
2. Give it a **name** (think carefully — it's immutable!).
3. Fill in **description** and especially **"When to use?"** — this decides whether
   the agent finds the skill at the right moment.
4. Under **Instructions** write the actual guide (Markdown: lists, headings, code
   blocks are allowed).
5. Optionally add **required tools** and **sources**.
6. Save.

## Toggle skills per agent

On an agent there's a **Skills tab**: there you see which skills are available for
that agent and can toggle them individually **on/off**. That way each agent gets
exactly the instructions that fit its role.

## Common mistakes

- **Agent never loads the skill** — The **"When to use?"** field is too vague.
  Phrase it concretely and situationally.
- **"Name invalid"** — Only `a-z`, `0-9`, `_`, `-`, max 50 characters.
- **Wrong name chosen** — It can't be changed afterwards; if in doubt, create a new
  one and delete the old.
- **Source unreachable** — If the URL needs a login, a matching **credential
  profile** must be stored and referenced in the skill.

## Tips

- **One skill = one purpose.** Prefer several small, clearly named skills over one
  overloaded one.
- **"When to use?" is the heart** — invest the most care here.
- **Use Markdown**: numbered steps and checklists make the guide most reliably
  followable for the agent.
- **Look at system skills** as templates to get a feel for good structure.
