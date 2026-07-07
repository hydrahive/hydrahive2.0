# Users

## What is this?

This is where you manage **who may log in to HydraHive** — the user accounts and
their roles. Only **admins** see this area. You also manage **API keys** here:
long-lived tokens that let external programs (e.g. a script or an MCP client)
access HydraHive without logging in via username/password.

## The two roles

- **Admin** — may do everything: create/edit/delete users, system settings,
  modules, VMs/containers, etc.
- **User** — normal working access (chat, projects, …) but without admin and
  system rights.

## Step by step

### Create a user
1. Click **New user**.
2. Choose a **username** (letters, digits, `_` and `-` only), e.g. `alice`.
3. Set a **password**.
4. Pick a **role** (admin or user).
5. Create — the user can now log in.

### Change password
Choose **Change password** on the user and set a new one. (As an admin you can do
this for others too.)

### Edit / delete a user
Via the actions on each entry. **You cannot delete yourself** — this prevents the
last admin from locking themselves out.

## API keys

An **API key** is a long-lived token for **machine access** — e.g. so a local tool
or script can use the HydraHive API without interactive login.

1. Give it a name (e.g. `claude-code-local`) → **Create key**.
2. **Important:** the key is shown **only once** — copy it immediately and store it
   safely. Afterwards it can't be viewed again.
3. **Revoke** (delete) keys you no longer need — the token stops working instantly.

## Common mistakes

- **"Username already exists"** — Name is taken, choose another.
- **"You cannot delete yourself"** — By design; delete yourself via a second admin
  account if truly needed.
- **API key lost** — Not recoverable; create a new one and revoke the old.

## Difference: user login vs. API key vs. credentials

- **Users** — humans logging in via the browser.
- **API key** — programs addressing HydraHive **from outside** (no login).
- **Credentials** (separate area) — access that HydraHive agents need to reach
  **outward** (e.g. a token for a foreign website). Don't confuse them.

## Tips

- **Be sparing with admin rights**: only those who really must manage need admin.
- **One API key per purpose/tool** — so you can revoke individual ones without
  affecting others.
- **Use strong passwords**, especially for admin accounts.
