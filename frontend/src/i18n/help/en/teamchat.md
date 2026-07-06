# Team chat — shared rooms for humans and agents

## What is this?

**Team chat** is a group chat where **several humans and several agents** write
together in a **room**. Unlike the Buddy chat (just you + your assistant), this is
a shared place — like a Slack or Discord channel, but right inside HydraHive and
with AI agents as full participants.

## Core terms

- **Room** — a chat channel. Can be **private** (invited members only) or **open**
  (discoverable/joinable).
- **Members** — the humans in the room. You see who's **online/offline**.
- **Attached agents** — AI agents that can read along and reply in the room.
- **@name** — with an `@` you address a specific agent (or person) directly.

## Step by step: set up a room

1. **New room** → give it a name, optionally add members (comma-separated) right
   away.
2. Choose visibility: **Private** or **Open**.
3. **Create**.
4. In the room, add one or more agents via **Attach agent**.
5. Start writing. Use **@name** to address a specific agent directly — without @ it
   runs as a normal group message.

## Manage members & agents

- **Add / remove member** — by username.
- **Attach / detach agent** — controls which AI is active in the room.
- **Discover** — find open rooms and **join**.

## When team chat instead of Buddy?

- **Buddy**: your private 1:1 assistant.
- **Team chat**: when **several people** should work with the same agent (or
  several agents) — e.g. a support room, a project room, a brainstorm with multiple
  specialist agents at once.

## Prerequisite

Team chat technically runs over a **Matrix server** (Tuwunel). If you see *"Team
chat is not enabled"*, that server is unreachable or team chat is switched off —
then it must first be enabled/set up under **Extensions**.

## Common questions

- **"The agent doesn't reply"** — Is it **attached** to the room? And did you
  address it with **@name**?
- **"I don't see the room"** — For private rooms you must be a **member**; open ones
  you find via **Discover**.
- **"Team chat is not enabled"** — The Matrix homeserver is unreachable or team chat
  is off; see **Extensions**.

## Tips

- **Multiple agents in one room**: handy to let different specialists speak at once
  — address them specifically via `@name`.
- **Open rooms** suit topics others should join spontaneously; **private** ones for
  confidential groups.
