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

### Set up Anthropic — three ways

Anthropic has **three** setup paths. All end up in the same "Anthropic" provider.
If you configure both a key and OAuth, **OAuth takes precedence**.

**Way 1 — classic API key (pay-per-use)**
1. Create an API key in the Anthropic Console (`sk-ant-api03-...`).
2. **Add provider** → **Anthropic** → paste the key into the **API-key field**.
3. Pick models, **Add**, **Test connection**. Billed at API prices (not via the
   subscription).

**Way 2 — subscription token via CLI (`claude setup-token`)**
Uses your Claude subscription (Pro/Max) instead of API credits. The token is
**generated in a shell with the Claude Code CLI** and pasted into the API-key
field — HydraHive detects the `sk-ant-oat...` prefix and treats it as OAuth.
1. In a shell with the Claude Code CLI: run `claude setup-token`.
2. Browser opens → **sign in and authorize** with your Claude account.
3. The long-lived token (`sk-ant-oat01-...`, ~1 year) appears **in the shell** →
   copy it.
4. **Add provider** → **Anthropic** → paste the token into the **API-key field**.
5. Pick models, **Add**, **Test connection**.

**Way 3 — OAuth login by click (subscription, no CLI)**
The most convenient path with a Claude subscription — no terminal needed.
HydraHive fetches the token itself and **refreshes it automatically**, so you
don't have to log in again every few days.
1. Click **Add provider** and select **Anthropic** in the dropdown. As soon as
   "Anthropic" is selected, the "or via OAuth login" area appears **below the
   API-key field**.
2. There, click **Open login** → sign in at **claude.ai** and authorize.
3. **Anthropic then shows a code directly on the page** (format `code#state`) —
   unlike ChatGPT there is **no URL to copy** here. Copy that **code**.
4. Paste the code in step two → **Connect**. It shows "Connected via OAuth".
5. Pick models, **Add**, set default model, **Test connection**.

> The API-key field stays visible in all three ways — the OAuth login (way 3) is
> an additional option, not a replacement.

### ChatGPT Plus/Pro (Codex) via OAuth login

ChatGPT also has an OAuth login button (no key needed):

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
