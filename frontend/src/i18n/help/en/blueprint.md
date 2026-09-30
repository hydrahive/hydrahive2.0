# Blueprint

## What is this?

**Blueprint** is a visual **node canvas** to **sketch layouts and flows** — instead
of laboriously describing them in words. You drag building blocks onto a canvas,
label them, and connect them. This lets you show an agent (or a colleague)
precisely how a page should look or a flow should work — a **non-verbal channel**
for design and functionality requests.

## What is it good for?

People and agents often talk past each other on UI/functionality requests: you
describe verbally, the other guesses. With Blueprint you hand over **layout blocks**
(page design) and **flow blocks** (process) directly — visual instead of ambiguous.

## Core terms

- **Board** — your canvas (you can have several).
- **Node/block** — an element on the board (dragged from the palette).
- **Connection** — links blocks into a flow.
- **Properties** — configurable per block on the right (label, details).

## Step by step

1. Create or open a **board**.
2. Drag blocks from the **palette** on the left onto the canvas.
3. **Label** blocks and **connect** them with lines.
4. Set details via the **properties panel** on the right.
5. The board then serves as a clear template — e.g. for an agent task.

## Handing a board to the agent

- **Right in the chat:** Write something like "Look at my board *Login page* and
  build it like that". The agent reads the board with the `blueprint_read` tool:
  every block with its label, placeholder and note, plus the connections, with
  **yes** and **no** on conditions. It only sees **your own** boards and never
  changes them.
- **Copy as text:** The button at the top of the editor puts the same text on the
  clipboard. You can paste it into any chat, even for agents without the tool.

The Buddy and your personal assistant get the tool automatically after the update.
Give it to other agents in the agent settings under **Tools**.

## Tips

- **Coarse before fine**: first the rough blocks and their connections, then
  details.
- **Don't forget labels** — an unlabeled box is as ambiguous as a vague
  description.
- **Several boards** for different ideas/pages rather than one overloaded one.
