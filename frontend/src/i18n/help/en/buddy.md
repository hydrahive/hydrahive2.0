# Buddy — your personal assistant

## What is this?

Buddy is the **home page** of HydraHive and your personal AI assistant. Unlike the **Workshop** (where you work with specialized agents on purpose), Buddy is your everyday companion: ask questions, jot things down, kick off tasks, keep an overview.

Buddy keeps **one continuous conversation** (a session) that persists — so you can always pick up where you left off. The animated **Hydra mascot** on the left shows its state: idle (waiting), working (thinking / using tools), or speaking (voice output).

Buddy is a full agent: it can **use tools** (read files, search the web, send email, generate images …) — you decide which ones in the settings.

## What can I do here?

- **Just start typing** — ask a question or give a task, press Enter. The answer streams in live.
- **Use commands** — messages starting with `/` are shortcuts (see below).
- **Pick a model** — the model selector at the top: which AI model Buddy currently uses.
- **Set project context** — bind Buddy to a project; its file tools then work inside that project's folder.
- **Control thinking depth** — the "Reasoning Effort" pill sets how thoroughly the model reasons (more depth = slower but more considered; only for models that support it).
- **Control cockpit slots** — music, extensions, games & widgets live in the right cockpit rail. You can collapse or hide slots; preferences are stored server-side per Buddy, not in browser localStorage.
- **See usage** — the usage chip shows the backend-provided provider, last-turn tokens and, when pricing is known, a rough cost estimate. If no pricing/quota data exists, it honestly says “price n/a”.
- **Customize Buddy** — the gear icon opens Buddy's settings (name, character, tools …).

## Key terms

- **Buddy session** — the single, ongoing conversation with your assistant. It stays saved until you start fresh with `/clear`.
- **Tools** — abilities beyond plain talk (web search, file access, mail, media generation …).
- **Compaction** — older messages get summarized so the conversation doesn't grow too long (and costly).
- **Reasoning Effort** — the model's thinking effort per reply (minimal/low/medium/high).
- **Soul / character** — Buddy's personality: name, tone (casual/professional/brief) and a free-form character text.

## Slash commands

Type one of these as a message:

| Command | Effect |
|---------|--------|
| `/help` | Shows this command list in the chat |
| `/clear` (or `/reset`) | Starts a fresh chat — the old session stays in history |
| `/remember [name]` | Saves the current conversation as a persistent note (memory) |
| `/model [name]` | Shows or switches Buddy's model |
| `/character` | Rolls a new character for Buddy |
| `/compact` | Manually compacts the current session (saves tokens) |
| `/tokens` | Shows token count and context window usage |
| `/title <text>` | Renames the Buddy session |
| `/system` | Shows the current system prompt |
| `/tools` | Lists the tools available in the backend |
| `/agent` | Shows info about the Buddy agent |
| `/soul` | Shows the building blocks of Buddy's personality |
| `/export` | Outputs the conversation as Markdown |

## Step by step

### Your first conversation

1. Buddy is already there when you open HydraHive (home page `/`).
2. Type your message below — e.g. *"Summarize what HydraHive can do"* — and press **Enter**.
3. Watch the answer stream in. If Buddy uses a tool (e.g. web search), you'll see it in the transcript.

### Bind Buddy to a project

1. Open the **project selector** at the top.
2. Pick a project — Buddy's file tools now work inside that project's folder.
3. To unbind, set it back to "no project".

### Configure Buddy's personality & tools

1. Top right: the **gear** (Buddy settings).
2. Tabs:
   - **Identity** — name, character text, language (de/en/auto), tone (casual/professional/brief).
   - **Context** — what Buddy should permanently know about you/your environment.
   - **Tools** — which tools Buddy may use (only enable what you actually need).
   - **Mail** — appears only when mail tools are active (mailbox access).
   - **Compaction** — when auto-compaction kicks in.
3. **Save**. Changing core identity may start a fresh session.

### Tidy up a long conversation

- If it gets very long, type `/compact` — older parts get summarized, the thread stays intact.
- To start over completely: `/clear`. The old transcript isn't lost, it just moves to the background.

## Common questions

- **"Buddy or Workshop — which one?"** Buddy = your personal everyday assistant (one ongoing conversation). Workshop = focused work with multiple specialized agents in separate sessions.
- **"Buddy doesn't answer / loads forever"** — Check that a model is set up under **LLM configuration** and a valid key is stored. Without a configured model Buddy can't think.
- **"Buddy can't do X (e.g. send mail)"** — The tool is probably not enabled. Gear → **Tools** → turn on the relevant tool.
- **"How does Buddy remember something permanently?"** — Use `/remember`, or put it in the **Context** tab.

## Tips

- **Enable tools sparingly**: fewer tools means Buddy picks the right one more reliably. Only enable what you use regularly.
- **Dose reasoning effort**: keep it low for quick questions, turn it up for tricky tasks.
- **Maintain context**: what Buddy should always know (your name, preferences, project environment) belongs in the **Context** tab — then you don't have to repeat it every message.
