# LLM Configuration

## What is this?

This is where you register **language model providers** with their API keys. HydraHive2 supports multiple providers in parallel — Anthropic, MiniMax, OpenAI and others can coexist, and each agent can pick which model it uses.

The **default model** is used when an agent doesn't explicitly set one.

## What can I do here?

- **Add provider** — pick from 7 preconfigured + custom
- **Manage API keys** (stored unencrypted in `~/.hh2-dev/config/llm.json`)
- **Pick models per provider** via clickable pills
- **Set the default model** — dropdown across all available models
- **Test connection** — sends `"Reply with exactly one word: OK"`
- **Remove provider** via the trash icon

## Key terms

- **Provider** — the vendor (Anthropic, OpenAI, MiniMax, Groq, Mistral, Gemini, OpenRouter)
- **API key / token** — credentials. Format differs:
  - Anthropic: `sk-ant-api03-...` (classic) or `sk-ant-oat01-...` (Claude-Max OAuth)
  - OpenAI: `sk-...`
  - MiniMax: JWT (`eyJ...`)
  - Gemini: `AIza...`
- **Default model** — used by agents without an explicit model
- **Context window** — token size the model can see at once (matters for compaction threshold)

## Step by step

### Set up Anthropic with a Claude subscription (Pro/Max) — OAuth token

With a Claude subscription (Pro/Max) you can use your account instead of a paid
API key. The OAuth token is **generated in a shell with the Claude Code CLI** and
pasted here into the normal API-key field — HydraHive detects the `sk-ant-oat...`
prefix and automatically treats it as an OAuth token.

1. In a shell with the Claude Code CLI installed, run:
   ```
   claude setup-token
   ```
2. Your browser opens → **sign in and authorize** with your Claude account
   (Pro/Max).
3. A long-lived token (`sk-ant-oat01-...`, valid ~1 year) then appears **in the
   shell**. Copy it.
4. Click **Add provider** → **Anthropic**.
5. Paste the `sk-ant-oat01-...` token into the API-key field (no OAuth login
   button needed — that's only for ChatGPT/Codex).
6. Pick models (e.g. `claude-sonnet-4-6`, `claude-opus-4-8`).
7. **Add**.
8. Set default model, click **Test connection** — should return "OK".

> Alternatively a classic API key from the Anthropic Console works too
> (`sk-ant-api03-...`) — that bills per usage at API prices instead of via the
> subscription.

### ChatGPT Plus/Pro (Codex) via OAuth login

This is the **only** provider with a real OAuth login button in the GUI (no key
needed):

1. **Add provider** → **ChatGPT Plus/Pro (Codex)**.
2. Click **Open login** → sign in at ChatGPT in the browser.
3. The browser redirects to `localhost:1455` and shows "site can't be reached" —
   **that's normal**. Copy the whole URL from the address bar.
4. Paste the URL in step two → **Connect**.

### MiniMax with token plan

1. **Add provider** → **MiniMax**
2. API key: your JWT (`eyJ...`)
3. Pick `MiniMax-M2.7`
4. **Add**
5. **Test connection**

### Multiple providers in parallel

You can have all relevant providers at once. When creating an agent you pick the desired model from the pool of all available ones.

## Common errors

- **`OAuth authentication is currently not supported`** — happens when LiteLLM sends the OAuth token as Bearer. HydraHive2 sidesteps this by using the Anthropic SDK directly — if you see this error check the backend log.
- **`Error code: 429 - rate_limit`** — over your token limit. Wait or use another provider.
- **`Error code: 401`** — wrong API key. Copy without whitespace.
- **`LLM Provider NOT provided`** (LiteLLM error) — the model name is unrecognized. Fix: pick the model from the dropdown instead of typing it.

## Tips

- **Use the suggested models** instead of typing — prevents typos in model names
- **For sensitive data**: use local models via Ollama (OpenAI-compatible endpoint) as a custom provider
- **Cost awareness**: Sonnet-4-6 is more expensive than Haiku — pick the right model per task
- **Token Plan (Claude Max)** instead of pay-per-use saves significantly on heavy use
