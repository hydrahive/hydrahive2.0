# Credentials — access data for web requests

## What is this?

This is where you store **access data (tokens, passwords, keys)** that your agents need to reach protected websites or services. The trick: you store an access secret **once** and define via a **URL pattern** what it applies to. When an agent then calls a matching address, the secret is **injected automatically** — the agent doesn't need to (and can't) know the token itself.

**Security (important):** Tokens **never** appear in the AI context or in tool results. They are only applied server-side during the actual network call and are stored encrypted. The model never "sees" your password.

## Why do I need this?

Examples:
- An agent should query a **private forum** or a **token-protected API**.
- An agent should connect to a server via **SSH** (e.g. to run commands there).
- A site requires a **cookie** or a **custom header** to serve content.

Without a matching credential the agent would just get "401 Unauthorized" or a login page.

## Credential types

| Type | For | How it's sent |
|------|-----|---------------|
| **Bearer Token** | API tokens, modern web APIs | `Authorization: Bearer <value>` |
| **Basic Auth** | classic username/password login | `Authorization: Basic <base64 of user:pass>` |
| **Cookie** | sites expecting session cookies | `Cookie: <value>` (e.g. `session=abc123`) |
| **Custom Header** | your own header names (e.g. `X-API-Key`) | your header name + value |
| **Query Parameter** | token appended to the URL | `…?<param>=<value>` |
| **SSH Key** | SSH access to a server | private key + host + user |

## Fields explained

- **Name** — free choice (only `a-z`, `0-9`, `_`, `-`) so you recognize the access.
- **Type** — one of the above. Matching extra fields appear per type.
- **Value** — the actual secret (token, `user:password`, cookie string …).
- **URL pattern** — determines which addresses the access applies to. A **glob pattern**:
  - `*` = for **all** URLs (use with care!)
  - `https://forum.example.com/*` = only this host and everything below it
- **Header name** / **Query param name** — only for "Custom Header" / "Query Parameter": what the field should be called.
- **Description** — optional note for yourself.

### Additionally for SSH keys
- **Private key (PEM)** — your private key in OpenSSH or PEM format. Stored encrypted, **never** passed to the model.
- **Hostname / IP** — the server to access.
- **SSH username** — the login name on the server.

## Step by step

### Store an API token (Bearer)

1. Click **New credential**.
2. Give it a **name** (e.g. `github-api`).
3. **Type** = Bearer Token.
4. **Value** = paste your token.
5. **URL pattern** = e.g. `https://api.github.com/*`.
6. Save. From now on the token is injected automatically when this API is called.

### Create an SSH access

1. **New credential** → **Type** = SSH Key.
2. Paste the **private key** (PEM/OpenSSH), set **host** and **username**.
3. Save. The agent can now connect to this host via SSH without knowing the key.

## Common mistakes

- **Agent still gets 401/login page** — The **URL pattern** doesn't match the actually called address. Check spelling and `*` placement.
- **"Name invalid"** — Only `a-z`, `0-9`, `_`, `-`, max 50 characters.
- **Pattern too broad** — `*` sends the access to **every** URL. Keep it as narrow as possible (just the one host) so a token isn't accidentally sent to foreign servers.

## Tips

- **As narrow as possible**: a URL pattern should only cover the hosts the access is really meant for.
- **One access, many agents**: all agents benefit automatically — you maintain the token in a single place.
- **Credentials vs. LLM keys**: this is about access to **external services**. The keys for the AI models themselves live under **LLM configuration**, not here.
