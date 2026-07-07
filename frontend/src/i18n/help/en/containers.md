# Containers

## What is this?

Containers are **lightweight, isolated services** — similar to VMs but much
leaner and faster. Technically they're **Linux containers (LXC via incus)**: they
share the host's kernel and start in seconds, without the overhead of a full
virtual machine.

**Rule of thumb:** Want a **complete foreign operating system** (e.g. Windows) →
use a **VM**. Want to run a **single Linux service** leanly (e.g. a search engine,
a password manager, a bookmark tool) → use a **container**.

## What is it good for?

Ideal for small, always-on services — examples suggested in the form: **searxng**
(search), **vaultwarden** (passwords), **linkding** (bookmarks). Each service runs
in isolation but can be reachable over the network.

## Core terms

- **Image** — the template a container is built from (e.g. an Ubuntu or Debian
  base image). Pick from the **quick images** or enter your own **image alias**.
- **Bridged / Isolated** — network mode (like VMs): bridged = own IP on the LAN,
  isolated = no network access.
- **CPU/RAM limit** — optional caps. Empty = unlimited (the container may take
  what's available).

## Step by step: create a container

1. Click **Create container**.
2. Give it a **name** (1–63 chars, starts with a letter, only `a-z A-Z 0-9 -`) —
   e.g. `searxng`.
3. Choose an **image** (from quick images or your own alias).
4. Optionally set a **CPU limit** and **RAM limit (MB)** — leave empty = unlimited.
5. Choose the **network**: **Bridged (br0)** for its own LAN IP, **Isolated** for
   no network access.
6. **Create container** → it starts and appears in the list.

## The detail view (tabs)

Clicking a container opens the detail view with four tabs:

- **Config** — settings (name, description, CPU/RAM, image). The image is
  read-only — to use a different image, re-create the container.
- **Console** — a shell inside the container, right in the browser.
- **Logs** — the lifecycle log (`incus info --show-log`), helps with boot problems.
- **Stats** — live usage (CPU/RAM) — only while the container runs.

## Common mistakes

- **"Image missing"** — No image chosen when creating. Pick one from the list or
  type a valid alias.
- **"Name invalid"** — 1–63 chars, starts with a letter, only `a-z A-Z 0-9 -`.
- **No live stats** — The container isn't running; start it first.
- **No network in the container** — Network is set to **Isolated**; switch to
  **Bridged**.

## Container or VM?

| | Container (LXC/incus) | VM (QEMU/KVM) |
|---|---|---|
| Weight | light, seconds to start | heavy, own kernel |
| OS | Linux (shares host kernel) | anything (incl. Windows) |
| Use for | single services | complete foreign systems |

## Tips

- **One service per container** — cleaner to maintain and restart.
- **Limits only when needed**: for most small services "unlimited" is fine; set
  limits when a container shouldn't overload the host.
- **Bridged** when you want to reach the service from other devices on the network.
