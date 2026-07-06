# Communication — messengers that reach your agent

## What is this?

On this page you connect **external messengers** to HydraHive so you can reach
your personal (master) agent **on the go** — without opening the web interface. If
you write on WhatsApp, for example, the message lands directly with your agent,
and its reply comes back the same way.

In short: your agent gets a "phone" you can text.

## Available channels

- **WhatsApp** — incoming messages go directly to your master agent.
- **Discord** — direct messages (DMs) and **@mentions** go to your master agent.

(Which channels are ready depends on your installation and the stored credentials.)

## What is it good for?

- You can give your agent tasks **on the go** ("Summarize my mail", "How's the
  server doing?").
- The agent can notify you **proactively** (e.g. via a Butler automation that posts
  a Discord message).
- No constant browser login needed — your familiar messenger is enough.

## Interplay with other areas

- **Butler**: incoming messages can serve as a **trigger** for automations ("When a
  Discord message with … → let agent reply").
- **Credentials**: connecting some services needs tokens/access — those live under
  *Credentials* or in the system settings.

## Common questions

- **"My WhatsApp message doesn't arrive"** — The connection isn't fully set up
  (access/token missing or expired). Check the channel's connection settings.
- **"Discord: agent doesn't react to normal messages"** — By default it reacts to
  **DMs** and **@mentions**. Address it directly.

## Tips

- **Start with one channel** (e.g. Discord) until the path works reliably before
  adding more.
- **Combine with Butler** if you want automatic reactions to incoming messages.
