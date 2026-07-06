# Getting started with HydraHive

Welcome! This page is your guiding thread. HydraHive is big — but you don't need
to understand everything at once. Here's the shortest path from "just logged in"
to "it works".

## What is HydraHive anyway?

HydraHive is a platform where **AI agents** work for you. An agent is an AI
assistant with a role, its own tools, and access to whatever you allow it. You
can talk to them, give them tasks, and let them do things automatically in the
background.

There are two main places to work:

- **Buddy** (the home page 🫀) — your **personal assistant** for everyday things.
  One ongoing conversation, always there for you.
- **Workshop** (💬) — for **focused work** with specialized agents in separate
  sessions (e.g. a coding agent for a project).

## Step 1 — Set up an AI model (required!)

Without a language model, no agent can think. This is the very first step.

1. Go to **Settings → LLM configuration** (gear at the top).
2. Enter your **API key** for a provider (e.g. Anthropic, OpenAI, OpenRouter —
   whatever you have).
3. Pick a **default model**.
4. Done — now Buddy and the agents can respond.

> If you later see "no model configured" everywhere or nothing happens, this step
> is usually the missing piece.

## Step 2 — Talk to Buddy

1. Click **Buddy** at the top left (the heart icon, home page).
2. Type a message below, e.g. *"What can you do for me?"* → **Enter**.
3. The answer streams in live. Buddy can use tools (web search, files …) — you
   choose which via Buddy's gear icon.

Buddy is the easiest entry point. Everything else builds on it.

## Step 3 — Create a project (when working on something concrete)

A **project** is a bounded workspace with its own file folder. Agents working in
a project only "see" its files — cleanly separated from everything else.

1. **Settings → Projects → New**.
2. Name it, optionally link a Git repo.
3. In **Buddy** or the **Workshop** you can then pick this project as context —
   the file tools will operate in its workspace from then on.

## Step 4 — Your own agents (when Buddy isn't enough)

If you need a specialist (e.g. "code reviewer", "research agent"), create one
under **Settings → Agents**: role, model, allowed tools. Then start sessions with
it in the **Workshop**.

## Where do I find what?

The left navigation is sorted into groups:

- **Overview** — dashboard (system state, activity).
- **Working** — Buddy, Workshop, Agents, Projects, Communication, Team chat.
- **Automation** — Butler (automations), Skills, MCP, Plugins.
- **Infrastructure** — VMs, containers, datamining, memory, and more.
- **Settings** (gear) — LLM, credentials, modules, users, system.

On many pages you'll find a **? icon** at the top — it opens help specific to
that page. Use it generously.

## Common pitfalls for newcomers

- **"Nothing responds / loads forever"** → Check step 1: model + valid API key
  under LLM configuration.
- **"The agent can't do X"** → The tool isn't enabled. Turn it on under **Tools**
  for the agent or Buddy.
- **"The agent can't reach a protected site"** → Store an access under
  **Credentials** (with a matching URL pattern).
- **"Where are my files?"** → In the **workspace** of the respective project.

## Recommended reading order

1. **Buddy** — your assistant (home page)
2. **LLM configuration** — so everything works
3. **Projects** — when working on something concrete
4. **Agents** — for specialists
5. **Workshop** — focused work
6. **Credentials** — as soon as external access is needed

Good luck — and don't worry, you don't need to master everything at once. Start
with Buddy.
