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

### Set up Anthropic OAuth (Claude Max)

1. Confirm your Token Plan subscription on https://claude.ai/settings/billing
2. Get your OAuth token (see Anthropic docs)
3. Click **Add provider** → **Anthropic**
4. Paste `sk-ant-oat01-...` into API key
5. Pick models (`claude-sonnet-4-6` etc.)
6. **Add**
7. Set default model, click **Test connection** — should return "OK"

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
