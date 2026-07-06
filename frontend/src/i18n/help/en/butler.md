# Butler — automations without programming

## What is this?

The **Butler** is your automation construction kit. On a canvas you build a rule
by **dragging and connecting** nodes: *"When X happens, and Y applies, then do
Z."* No code — you plug the building blocks together like a flowchart.

Example: *"When an email arrives from my boss (trigger), and it contains the word
'urgent' (condition), then let agent 'Assistant' reply (action)."*

Such a rule is called a **flow**. You can have several flows and switch each one
**active** or **inactive** individually.

## The three building blocks

A flow always reads left to right: **trigger → condition(s) → action(s)**. Only
the trigger is required — conditions are optional.

### 1. Trigger (the "When …")

What should start it?

- **Message received** — an incoming message to an agent.
- **Webhook received** — an external service calls a URL (you get a hook URL to
  copy).
- **Heartbeat fired** — time-based/recurring (for regular tasks).
- **Git event** — e.g. a push or change in a repository.
- **Discord event** — e.g. a reaction or message in a channel.
- **Email received** — an incoming email.

### 2. Conditions (the "… and if it applies …")

Refine when the flow should actually fire. Each condition has a **Yes/No** output:

- **Time window** / **Day of week** — only at certain times.
- **Contact known** — only from known senders.
- **Message contains** / **Field contains** — text filters on content.
- **Git: branch / author / action is …** — filters on Git events.
- **Email: sender / subject / body contains …** — filters on emails.
- **Discord: event type / emoji is …** — filters on Discord.

### 3. Actions (the "… then do …")

What should happen?

- **Agent reply** — an agent handles the message freely.
- **Agent reply with instruction** — agent replies, guided by your prompt.
- **Fixed reply** — always the same predefined text.
- **Queue** / **Ignore** — set aside for later or discard.
- **Forward** — hand over to another agent.
- **HTTP POST** — call an external URL (with JSON body).
- **Send email**.
- **Git: create issue / add comment** — create something in the repository.
- **Discord post** — write a message into a channel.

## Step by step: build your first flow

1. Drag a **trigger** from the palette (left) onto the canvas.
2. Drag an **action** in and **connect** the two (drag from the trigger's output
   to the action's input).
3. Optional: insert a **condition** in between — connect its **Yes** output to the
   action.
4. Click a node → set the details in the **Properties panel** on the right (e.g.
   which agent, which channel, which text filter).
5. Give the flow a **name** at the top and click **Save**.
6. Test safely with **Dry run**: the flow is played through with a test event —
   **no real actions** are executed. You see whether the trigger matches and how
   many actions would run.
7. When it's right: switch the flow to **Active**.

## Common mistakes

- **"Not active yet — no backend event sender available"** — The chosen trigger
  isn't (yet) wired to a real event source in your installation. The flow saves
  but won't fire until the source exists.
- **"Save the flow first, then dry run"** — Dry run only works with a saved flow.
- **Action never runs** — Check the **connections**: is the trigger actually
  connected to the action? With conditions: is the action on the **Yes** output?
- **Discord channel missing** — You need the **numeric channel ID** (in Discord:
  right-click the channel → Copy ID).

## Tips

- **Dry run first, then activate.** The dry run is harmless — always use it before
  going live.
- **Start small**: trigger + one action. Add conditions later.
- **Several flows** instead of one giant flow — one per purpose, individually
  toggleable, much clearer.
- **Project context**: flows belong to the current project — make sure you're in
  the right one.
