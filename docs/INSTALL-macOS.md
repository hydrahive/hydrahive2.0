# Installing HydraHive on a Mac – step by step

> **Status: experimental.** HydraHive runs on a Mac, but the Mac installer is simpler than the Linux installer.
> Some features are not available on a Mac (see [What does not work on a Mac](#what-does-not-work-on-a-mac)).
> For a server that runs around the clock we recommend Linux (Ubuntu).
> Last tested: 23 October 2026 on an Intel iMac (macOS 15.3) and a MacBook Air M2 (macOS 27): fresh install, moving
> older installations by update, containers, Tailscale and Voice.

Deutsche Fassung: [INSTALL-macOS.de.md](INSTALL-macOS.de.md) ·
Having an AI do the install? → [Summary for AI assistants](#summary-for-ai-assistants)

---

## Contents

0. [Before you start – the key questions](#0-before-you-start--the-key-questions)
1. [Check: which Mac do I have?](#1-check-which-mac-do-i-have)
2. [Log in to the Mac – with the right user](#2-log-in-to-the-mac--with-the-right-user)
3. [Finding and using Terminal](#3-finding-and-using-terminal)
4. [Install Homebrew](#4-install-homebrew)
5. [Download HydraHive](#5-download-hydrahive)
6. [Run the installer – and what happens next](#6-run-the-installer--and-what-happens-next)
7. [Open it in your browser and log in](#7-open-it-in-your-browser-and-log-in)
8. [Set up the AI (otherwise Buddy won't answer)](#8-set-up-the-ai-otherwise-buddy-wont-answer)
9. [Check that everything is running](#9-check-that-everything-is-running)
- [What does not work on a Mac](#what-does-not-work-on-a-mac) · [Things to watch out for](#things-to-watch-out-for) ·
  [Useful commands](#useful-commands) · [Troubleshooting](#troubleshooting) · [Uninstalling](#uninstalling) ·
  [Summary for AI assistants](#summary-for-ai-assistants)

---

## 0. Before you start – the key questions

| Question | Answer |
|---|---|
| **How long does it take?** | 30–60 minutes. Most of it is waiting for downloads. |
| **Do I need to know how to program?** | No. You copy commands from this guide into the **Terminal** app. Every command is here, ready to copy. |
| **Do I need a special user?** | **No, but it has to be an administrator.** You install with your normal Mac user account if it has administrator rights. HydraHive itself then runs under its own hidden account `_hydrahive`, which the installer creates (see [step 6](#6-run-the-installer--and-what-happens-next)). HydraHive still needs your account for Homebrew. |
| **Which password will I be asked for?** | Always **the password you use to log in to your Mac**. Only at the very end do you get a new, random password for HydraHive. |
| **Do I need internet?** | Yes, for the whole installation. |
| **Does it cost anything?** | HydraHive and everything it installs are free. For the AI itself you then need either an account with an AI provider (pay per use) or a local model via Ollama (free, but needs a lot of memory). |
| **What if something goes wrong?** | Just run the installer again. Anything already installed is skipped. There is also the [troubleshooting](#troubleshooting) section and our [Discord](https://discord.gg/GVCZvNxxFA). |

**What you need:**

| | Minimum | Recommended |
|---|---|---|
| **Mac** | Apple Silicon (M1 or newer). Intel works only with limitations, see [step 1](#1-check-which-mac-do-i-have) | Apple Silicon |
| **macOS** | 13 (Ventura). Homebrew considers 13–14 "not officially supported", but it usually works | 15 (Sequoia) or newer |
| **Memory** | 8 GB | 16 GB or more (32 GB+ with local AI models) |
| **Free disk space** | 15 GB | 30 GB+ |
| **User account** | one with **administrator rights** | |

---

## 1. Check: which Mac do I have?

1. Click the **Apple menu ** in the top-left corner.
2. Choose **"About This Mac"**.
3. Look at the **"Chip"** or **"Processor"** line and at the **"macOS"** line.

| It says … | Meaning |
|---|---|
| **Chip: Apple M1 / M2 / M3 / M4 …** | ✅ Apple Silicon. This guide fits exactly. |
| **Processor: … Intel Core …** | ⚠️ Intel Mac. Read the box below **before** you continue. |
| **macOS 12 or older** | ❌ too old. Update macOS first (System Settings → General → Software Update). |

> ### ⚠️ Intel Macs: status October 2026
> HydraHive needs Homebrew to install. Homebrew cut back its Intel Mac support heavily in September 2026:
> - The **official install script** from brew.sh stops on Intel with
>   `Homebrew on macOS is only supported on Apple Silicon processors!`
> - Homebrew **no longer builds new ready-made packages** for Intel. Some programs are then compiled from source on
>   your Mac, which can take **hours**.
> - From September 2027 Homebrew is expected to stop running on Intel entirely.
>
> **Is Homebrew already installed on your Intel Mac?** Type `brew --version` in Terminal (see step 3). If a version
> number appears, you can skip step 4. Our October 2026 test ran this way.
>
> **No Homebrew yet?** Then the Mac route is a struggle. We recommend installing HydraHive on a Linux machine or using
> an Apple Silicon Mac. A fallback is described in [Troubleshooting → Intel Mac without Homebrew](#intel-mac-without-homebrew).
> We have not tested it.

---

## 2. Log in to the Mac – with the right user

You **log in to the Mac as usual**, the way you do every day on the login screen with your name and password.
The only requirement is that the account has **administrator rights**.

**How to check:**

1. **Apple menu ** → **System Settings**.
2. Click **"Users & Groups"** in the list on the left.
3. Does it say **"Admin"** under your name? → ✅ You're fine.
   Does it say "Standard"? → You need a different account. Log in with an account that says "Admin", or ask whoever
   owns the Mac to give you administrator rights.

**Make a note of your account's short name.** You won't necessarily need it, but it helps with problems.
You can find it in Terminal with the command `whoami`.

> **You don't need to create an account for HydraHive.** The installer does that: HydraHive runs under the hidden
> system account `_hydrahive` (see [step 6](#6-run-the-installer--and-what-happens-next)).

> **The Mac is somewhere else? Remote login via SSH.** On the Mac, turn on **System Settings → General → Sharing →
> "Remote Login"**. Then, from another computer, type `ssh yourshortname@IP-of-the-Mac` in a terminal. The IP address
> is shown under **System Settings → Wi-Fi** or **Network → Details**. All further commands work the same way. The one
> exception: the window in step 4a appears on the Mac's own screen.

---

## 3. Finding and using Terminal

**Terminal** is an app that comes with every Mac. You type or paste the commands into it.

### Opening Terminal – two ways

**Option A: Spotlight (fastest)**
1. Press **⌘ (Command) + Space** at the same time. A search field appears in the middle of the screen.
2. Type `Terminal`.
3. Press **Return**.

**Option B: via Finder**
1. Click **Finder** in the Dock (the bar at the bottom, the blue-and-white face).
2. Click **"Applications"** on the left.
3. Open the **"Utilities"** folder.
4. Double-click **"Terminal"**.

### What Terminal looks like

A window with a line like this:

```
anna@Annas-MacBook ~ %
```

This is the **prompt**. The `%` at the end means "I'm waiting for a command."

### Running a command

1. **Copy** the command from this guide. On GitHub every grey box has a **copy icon** (two rectangles) in its
   top-right corner. Or select the text and press **⌘ + C**.
2. Click into the Terminal window.
3. Press **⌘ + V** (paste).
4. Press **Return**.
5. **Wait** until the prompt with `%` appears again. Only then is the command finished.

> **Password prompt:** If Terminal shows `Password:`, type **your Mac login password** and press **Return**.
> **Nothing appears while you type**, no dots and no asterisks. That's normal, the password is still being entered.
> If it then says `Sorry, try again`, you mistyped it. Just try again.

> **A command hangs or you want to cancel?** Press **Ctrl + C** (the "control" key, not ⌘).

---

## 4. Install Homebrew

**Homebrew** is a program that installs other programs (Python, Node.js, the database …).
The HydraHive installer needs it.

**Already installed?** Check first:

```bash
brew --version
```

- Does it show `Homebrew 4.x.x` or higher? → **Continue with step 5.**
- Does it show `zsh: command not found: brew`? → Continue with 4a.

### 4a. Apple developer tools

```bash
xcode-select --install
```

- A **window** opens → click **"Install"** → **"Agree"** to the licence → wait (5–15 minutes).
- If you see `… Command line tools are already installed …` instead, they're already there. Continue with 4b.

### 4b. Homebrew itself

The command comes from the official site [brew.sh](https://brew.sh):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

What happens next:
1. If `Password:` appears → type your **Mac password**, press Return.
2. A list of what will be installed, then
   `Press RETURN/ENTER to continue or any other key to abort:` → press **Return**.
3. Wait (5–15 minutes). At the end you'll see **`==> Installation successful!`**.

### 4c. Make Homebrew permanent (important!)

At the very bottom Homebrew shows a **`==> Next steps:`** section with **one to three commands**. Copy and run
**exactly those**, one after the other. On an Apple Silicon Mac they look like this:

```bash
echo >> ~/.zprofile
echo 'eval "$(/opt/homebrew/bin/brew shellenv zsh)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv zsh)"
```

If Homebrew shows no such commands, there's nothing to do.

**Check:** quit Terminal completely (**⌘ + Q**), open it again (step 3) and type:

```bash
brew --version
```

✅ `Homebrew 4.x.x` or higher → continue.
❌ `command not found` → repeat 4c, using exactly the commands from **your** Terminal window.

---

## 5. Download HydraHive

HydraHive goes into the folder **`/opt/hydrahive2`**. That's where the installer looks for it.
Run these five commands **one at a time**:

```bash
brew install git
```
```bash
sudo mkdir -p /opt/hydrahive2
```
→ asks for your Mac password.
```bash
sudo chown "$(whoami)" /opt/hydrahive2
```
```bash
git clone https://github.com/hydrahive/hydrahive2.0.git /opt/hydrahive2
```
→ downloads HydraHive. At the end it says `Resolving deltas: 100% … done.`
```bash
cd /opt/hydrahive2
```

**Check:**

```bash
ls /opt/hydrahive2/installer/install-mac.sh
```

✅ It shows `/opt/hydrahive2/installer/install-mac.sh` → continue.
❌ `No such file or directory` → the `git clone` failed. Read the error message above it. If it says
`already exists and is not an empty directory`, something is already there. See
[Troubleshooting](#the-folder-opthydrahive2-already-exists).

---

## 6. Run the installer – and what happens next

```bash
cd /opt/hydrahive2
bash installer/install-mac.sh
```

> ⚠️ Do **not** type `sudo bash …`! The installer runs as **your** user and asks for the password itself when it needs
> it. Homebrew belongs to you and refuses the system account "root".

> ℹ️ **HydraHive gets its own account.** The installer creates a hidden system account `_hydrahive` (not shown on the
> login screen, no password). HydraHive runs under that account, not under your user. Reason: since macOS 15 the
> "Local Network" privacy setting blocks every program of the logged-in user from the home network, background
> services included. Under its own account HydraHive reaches devices on your network (port forwards, Home Assistant,
> other computers), and it cannot read your private files.

### What you'll see in Terminal

The installer works in phases. Each one starts with a turquoise line `[hh2-mac] Phase …`:

| Phase | What happens | Time (approx.) | Do you need to do anything? |
|---|---|---|---|
| **0** Service account | Creates the hidden account `_hydrahive` | seconds | **yes: `Password:` → Mac password** |
| **1** System dependencies | Installs Python 3.12, Node.js, git, ffmpeg, GitHub CLI, `uv` and `mmx-cli` | 5–20 min | no |
| **2** Directories | Creates folders for data and settings | seconds | **yes: `Password:` → Mac password** |
| **3** Python venv + backend | Sets up the program in the background | 2–5 min | no |
| **4** Frontend | Builds the web interface | 3–10 min | no |
| **5** PostgreSQL | Installs the database for memory and search and sets it up as a background service | 2–5 min | **maybe `Password:`** |
| **6 / 6b** launchd service | Sets HydraHive up as a background service that starts at boot | seconds | **maybe `Password:` again** (also possible in phase 7) |
| **6c** AgentLink | Sets up AgentLink so agents can hand tasks to each other and servers can be paired (own database in PostgreSQL, two background services) | 2–5 min | **maybe `Password:`** |
| **6d** Containers (optional) | Only with `--with=containers`: small Linux VM with Incus (Colima), see [Containers](#containers-optional) | 3–10 min | no |
| **6e** Tailscale (optional) | Only with `--with=tailscale`: builds Tailscale without the app and sets it up as a service, see [Tailscale](#tailscale-optional) | 1–3 min | no |
| **6f** Voice (optional) | Only with `--with=voice`: speech input and read-aloud directly on the Mac, see [Voice](#voice-optional) | 1–5 min | no |
| **7** nginx | Sets up the web server with HTTPS | 1–2 min | no |

**Stay nearby.** macOS only remembers your password for 5 minutes. If phases 3–5 take longer, the installer asks
again in phase 6. It simply waits until you enter it.

In between you'll see many lines like `· brew install python@3.12` or `· npm install`. Yellow warnings
(`npm warn …`, `Warning: …`) are usually harmless. **Red messages after which the installer stops** are real errors.
See [Troubleshooting](#troubleshooting).

### The end: the green box

Last comes `Warte auf den ersten Start (Admin-Passwort) …` ("waiting for first start"). This can take up to a minute.
Then you'll see:

```
╔══════════════════════════════════════════════╗
║     HydraHive2 — Installation fertig (Mac)   ║
╠══════════════════════════════════════════════╣
║  URL:       https://192.168.1.50             ║
║  Benutzer:  admin                            ║
║  Passwort:  Xy7_kQ2mP9vLr4Tz                 ║
╠══════════════════════════════════════════════╣
```

("Benutzer" = user, "Passwort" = password.)

> ### ⚠️ Write the password down right away!
> This is your **HydraHive password** for the user `admin`. It is **not** your Mac password and is shown **only this
> once**. Write it down or save it in your password manager.
>
> If it says `(nicht neu – siehe Anleitung)` ("not new – see guide"), see
> [Troubleshooting → Admin password missing](#admin-password-missing).

**The installation is done.** You can leave Terminal open or close it. HydraHive keeps running in the background
and starts by itself every time the Mac boots.

---

## 7. Open it in your browser and log in

1. Open a browser (Safari, Chrome or Firefox).
2. Type into the address bar:
   - **On the same Mac:** `https://localhost`
   - **From another device on the same Wi-Fi** (phone, laptop): the **URL from the green box**, e.g.
     `https://192.168.1.50`

### The security warning is expected

HydraHive issued its own certificate. Your browser doesn't know it and warns you. The connection is still encrypted.

- **Safari:** "Show Details" → "visit this website" → "Visit Website" again (Safari may ask for your Mac password)
- **Chrome:** "Advanced" → "Proceed to … (unsafe)"
- **Firefox:** "Advanced…" → "Accept the Risk and Continue"

### Log in

1. **Username:** `admin`
2. **Password:** the password from the green box
3. **Set your own password right away:** open `https://localhost/profile`. Alternatively, click the **circle with
   your initial** at the top or bottom → **Profile**. Then **"Change password"**: enter the current password, enter a
   new password (at least 8 characters), save.

---

## 8. Set up the AI (otherwise Buddy won't answer)

After installing, **no AI model** is set up yet. Without a model, Buddy won't answer.

1. Open `https://localhost/llm`. Alternatively: **Settings → AI models**.
2. Click **"Add provider"**.
3. Pick a provider and enter your access:

| Option | For whom | What you need |
|---|---|---|
| **API key** (Anthropic, OpenAI, OpenRouter, Mistral, Gemini, NVIDIA …) | fastest start | a key from the provider (starts e.g. with `sk-…`); pay per use |
| **Anthropic via login** or **ChatGPT Plus/Pro (Codex)** | if you already have a subscription | the login button in the form, no key needed |
| **Ollama (local)** | privacy, offline | lots of memory; instructions below |

4. Save. Then pick a model as the default under **"Default models"**.
   For **memory** (Buddy finds earlier conversations even when different words were used) you also need an
   **embedding model** there, e.g. `text-embedding-3-small` (OpenAI) or `baai/bge-m3` (OpenRouter). Without an
   embedding model, search only finds places where the exact word appears.
5. **Test:** open `https://localhost/buddy` and write "Hello". Do you get an answer? → 🎉 Done!

> No models showing up after a login? Restart the service once, see [Useful commands](#useful-commands).

### Optional: local models with Ollama

```bash
brew install ollama
brew services start ollama
ollama pull qwen3:8b
```

`qwen3:8b` is a download of about 5 GB. With 8 GB of RAM, choose a smaller model such as `qwen3:4b`.
Then in HydraHive choose **"Ollama (local)"** under **Add provider**. Address: `http://localhost:11434`.
Details: [ollama-provider.md](ollama-provider.md)

---

## 9. Check that everything is running

```bash
sudo launchctl list | grep io.hydrahive
```

Expected: eight lines with `io.hydrahive.backend`, `io.hydrahive.nginx`, `io.hydrahive.postgres`,
`io.hydrahive.agentlink`, `io.hydrahive.agentlink-frontend`, `io.hydrahive.update`, `io.hydrahive.restart` and
`io.hydrahive.addon`. The add-on modules add `io.hydrahive.colima` (containers), `io.hydrahive.tailscaled` (Tailscale)
and `io.hydrahive.voice-stt` / `io.hydrahive.voice-tts` (Voice). A **number** in the first column means the service is
running. A `-` is normal for `update`, `restart` and `addon`, which only run when needed.

> **Installed before October 2026?** Then AgentLink is missing (the two `agentlink` lines). A normal update in the
> cockpit (Settings → System → Update) adds it.

```bash
curl -sk https://localhost/api/health
```

Expected: a line containing `"status":"ok"`.

```bash
"$(brew --prefix postgresql@16)/bin/pg_isready" -h 127.0.0.1
```

Expected: `127.0.0.1:5432 - accepting connections` (the database). On a Mac set to German it says
`Verbindungen werden angenommen`.

```bash
curl -s http://127.0.0.1:9000/health
```

Expected: `"status":"healthy"` and `"redis":"memory"` (AgentLink). On a Mac AgentLink runs without Redis – Homebrew
only offers Redis for Intel Macs as a source build, which would take hours. The cockpit home page shows
“AgentLink connected”.

---

## What does not work on a Mac

The Mac installer only sets up the **core**. The following is **not** available on a Mac (or only by hand):

| Feature | On a Mac | Why |
|---|---|---|
| **Containers** (Incus) | ✅ optional | through a small Linux VM (Colima), see [Containers](#containers-optional) |
| **VMs** (libvirt/QEMU) | ❌ not available | Linux only |
| **Voice** (speech input + read-aloud) | ✅ optional | directly on the Mac, no containers: Settings → Add-on modules → Voice (or `--with=voice`), see [Voice](#voice-optional) |
| **WhatsApp integration** | ❌ not set up | the bridge is only set up by the Linux installer |
| **Samba shares** (project folders on the network) | ❌ not available | Linux module |
| **Tailscale remote access & server pairing** | ✅ optional | automatically via Settings → Add-on modules → Tailscale (or `--with=tailscale`), see [Tailscale](#tailscale-optional). Alternatively the Tailscale app – **not both** |
| **Web search (SearXNG)** | ⚠️ not automatic | enter your own SearXNG address in the settings, otherwise `web_search` won't work |
| **Starter agents & MCP servers** | ⚠️ not automatic | Linux creates them during install; on a Mac create them by hand in the cockpit |
| **Local media models** (image/video with an NVIDIA GPU) | ❌ not available | needs NVIDIA + Docker |
| **Extensions** (Settings → Extensions) | ⚠️ mostly not | many need `apt`/`docker` and fail with an unclear error |
| **Modules** (Settings → Modules) | ✅ almost all | tested: 21 of 22; **OpenTor** doesn't work (Tor only via Linux packages) |
| **Firewall rules** (ufw) | ❌ | macOS uses its own firewall |

**What works well:** cockpit, Buddy, agents, projects, workshop, datamining/memory, tasks, AgentLink (agents hand tasks
to each other), modules such as Atelier, Storyteller, Household book and so on, and updates through the cockpit.

---

## Things to watch out for

- **The Mac has to stay awake.** HydraHive only runs while the Mac is on and **not asleep**. For continuous operation:
  **System Settings → Energy** (on a laptop: **Battery → Options**) → prevent sleeping when the display is off.
  Keep laptops plugged in.
- **After a restart** HydraHive, the web server and the database start by themselves, even if nobody logs in.
- **Don't delete the `_hydrahive` account.** HydraHive runs under it. Your own user is only needed for Homebrew.
- **Files in your home folder** (Desktop, Documents …) are not visible to HydraHive. Upload what it should work on
  in the cockpit.
- **Ports 80 and 443** are taken by HydraHive (nginx). If another web server is already running on the Mac, they will
  conflict.
- **Access from the network:** other devices reach HydraHive via the Mac's IP address. If the address changes, e.g.
  on a different Wi-Fi, the certificate no longer quite matches and the browser warning comes back.
- **macOS firewall:** if macOS asks whether `nginx` may accept incoming connections, click **"Allow"**.
- **Backups:** your data lives in `/usr/local/var/hydrahive2`, the settings (including keys) in
  `/usr/local/etc/hydrahive2`. Back up these two folders. Time Machine includes them.

---

## Containers (optional)

HydraHive can manage containers on a Mac – in the interface (**Containers**) and through agents (`incus …`), just
like on Linux. A small **Linux VM** (Colima with Incus) runs in the background for this.

**Turn it on** – either way:
- during installation: `bash installer/install-mac.sh --with=containers`
- later: **Settings → Add-on modules → Containers → Install** (takes a few minutes)

| | Default | change with |
|---|---|---|
| VM cores | 2 | `HH_CONTAINERS_CPU` (at most half of the Mac) |
| VM memory | 4 GB | `HH_CONTAINERS_MEMORY` (at most half of the Mac) |
| Space for containers | 60 GB | `HH_CONTAINERS_DISK` |

**Good to know:**
- The VM permanently uses memory (about 1–2 GB actually in use). That is why the option is off by default.
- Network: containers sit in their own network 10.10.0.0/24 (like on a VPS). Joining the home network directly
  ("bridged" mode) is not possible on a Mac.
- **Publishing ports** (Containers → Ports): "public" listens on all addresses of the Mac, "tailnet" only on the
  Tailscale address. **TCP only**. The container sees the VM as sender, not the real visitor.
- After a restart of the Mac the VM starts by itself (service `io.hydrahive.colima`), even without login. Published
  ports are reachable again at most 30 seconds after HydraHive starts.
- Real VMs (not containers) are not available on a Mac.

**Check:**

```bash
sudo launchctl list | grep io.hydrahive.colima
cd /tmp && sudo -u _hydrahive env HOME=/usr/local/var/hydrahive2/home COLIMA_HOME=/usr/local/var/hydrahive2/colima /usr/local/lib/hydrahive2/containers/bin/incus list
```

The VM belongs to the `_hydrahive` account. Run as your own user, `incus` won't find it.

Problems: log at `/usr/local/var/log/hydrahive2-colima.log` or `hydrahive2-addon.log`.

---

## Tailscale (optional)

Tailscale connects the Mac securely to your other devices and servers – for remote access and for **pairing with
another HydraHive** (agents hand tasks to agents on the other server).

**Turn it on:** Settings → Add-on modules → **Tailscale → Install** (or `--with=tailscale` during installation).
HydraHive builds Tailscale once (about 1–3 minutes) and sets it up as a service that starts at boot – **without the
Tailscale app** and without any approval on screen.

**Sign in:** Settings → System → Tailscale → **"Sign in with browser"** → open the link → sign in with your Tailscale
account. Alternatively "Connect with auth key".

**Good to know:**
- If the **Tailscale app** is already installed, HydraHive uses it and installs nothing extra. Both at the same time
  do not get along.
- This variant cannot use someone else's exit node; Taildrop is limited. Remote access and pairing work fully.
  Updates come with the normal HydraHive update.
- Check: `sudo launchctl list | grep io.hydrahive.tailscaled`, log `/usr/local/var/log/hydrahive2-tailscaled.log`.

---

## Voice (optional)

Speech input (microphone in chat, voice messages, `transcribe_audio`) and read-aloud – local, no cloud.

**Turn on:** Settings → Add-on modules → **Voice → Install** (or `--with=voice` when installing). No containers
needed on the Mac: speech recognition (Whisper) and the voice (Piper) run as two background services directly on the
Mac and start at boot.

**Good to know:**
- Takes about 1–5 minutes. On first start, speech recognition downloads its model (~460 MB).
- Disk about 1.1 GB, memory about 400 MB while the service runs.
- Updates come with the normal HydraHive update.
- Check: `sudo launchctl list | grep io.hydrahive.voice`, logs
  `/usr/local/var/log/hydrahive2-voice-stt.log` and `…-voice-tts.log`.

---

## Useful commands

| What | Command |
|---|---|
| Restart the service | `sudo launchctl kickstart -k system/io.hydrahive.backend` |
| Is the service running? | `sudo launchctl list \| grep io.hydrahive` |
| Is the database running? | `"$(brew --prefix postgresql@16)/bin/pg_isready" -h 127.0.0.1` |
| Restart the database | `sudo launchctl kickstart -k system/io.hydrahive.postgres` |
| Database log | `tail -50 /usr/local/var/log/hydrahive2-postgres.log` |
| Add-on modules log | `tail -50 /usr/local/var/log/hydrahive2-addon.log` |
| Show error log | `tail -50 /usr/local/var/log/hydrahive2-error.log` |
| Show update log | `tail -50 /usr/local/var/log/hydrahive2-update.log` |
| Web server errors | `tail -50 /usr/local/var/log/nginx-hydrahive-error.log` |

### Updates

Easiest through the update function in the cockpit. By hand:

```bash
sudo bash /opt/hydrahive2/installer/update-mac.sh
```

The script detects the service user by itself.

**Older installations** (before the own account) are moved to `_hydrahive` once by the next update. It takes a few
minutes; HydraHive is briefly unreachable. The update first makes a backup (`/usr/local/var/hydrahive2-backup-<date>`:
settings, chats, database). If a step fails, it restores the previous state and retries with the next update. To opt
out, put `HH_SERVICE_ACCOUNT=no` into `/usr/local/etc/hydrahive2/install.conf`.

**Commands in the HydraHive folder** (e.g. `git`) now run as that account:

```bash
cd /tmp && sudo -H -u _hydrahive git -C /opt/hydrahive2 log --oneline -3
```

`cd /tmp` and `-H` matter: otherwise git complains about your own home folder. Run as your own user, git reports
"dubious ownership" because the folder now belongs to the account.

---

## Troubleshooting

### `brew: command not found`
Homebrew is not on the search path. Run [step 4c](#4c-make-homebrew-permanent-important), then close Terminal and
open it again.

### `… is not in the sudoers file` or the password is never accepted
Your account is not an administrator. See [step 2](#2-log-in-to-the-mac--with-the-right-user).

### `Homebrew on macOS is only supported on Apple Silicon processors!`
You have an Intel Mac. See the box in [step 1](#1-check-which-mac-do-i-have) and
[Intel Mac without Homebrew](#intel-mac-without-homebrew).

### Intel Mac without Homebrew
**A fallback we have not tested.** The last version of the official Homebrew install script that still supported
Intel (from 4 August 2026) is still in the Homebrew repository:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/f4aa1b1ca5b256954dbde0315455fb259cdfc45a/install.sh)"
```

Then continue with 4c. On Intel the paths are `/usr/local/bin/brew` instead of `/opt/homebrew/bin/brew`. Expect some
programs to be compiled from source, which makes the installation take much longer.

### The folder `/opt/hydrahive2` already exists
It's left over from an earlier attempt. If there is **no** working installation in it, you can delete it and repeat
step 5:

```bash
sudo rm -rf /opt/hydrahive2
```

### Admin password missing
The green box shows `(nicht neu – siehe Anleitung)`. There are two reasons for this:

1. **You ran the installer a second time.** The user `admin` already exists, so no new password is generated. Use the
   password from the first run.
2. **The service took longer than a minute to start.** Then the password is still in a file:

   ```bash
   sudo cat /usr/local/etc/hydrahive2/.admin_initial_password
   ```

   If that file doesn't exist, look in the error log:

   ```bash
   grep -A3 "Erster Start" /usr/local/var/log/hydrahive2-error.log
   ```

Change the password right afterwards (step 7). Otherwise it stays in the log.

### Installer stops at `npm install` ("network", "ECONNRESET")
Usually a short network hiccup during a download. **Just run the installer again.** Programs that are already
installed are skipped.

### Browser: "connection refused" / the page doesn't load
1. Is the service running? → `sudo launchctl list | grep io.hydrahive`
2. Look at the error log → `tail -50 /usr/local/var/log/hydrahive2-error.log`
3. Restart the service → `sudo launchctl kickstart -k system/io.hydrahive.backend`

### Datamining/search doesn't work
1. Is the database running? → `"$(brew --prefix postgresql@16)/bin/pg_isready" -h 127.0.0.1`
2. If not: `sudo launchctl kickstart -k system/io.hydrahive.postgres`, then
   `sudo launchctl kickstart -k system/io.hydrahive.backend`
3. Look at the database log → `tail -50 /usr/local/var/log/hydrahive2-postgres.log`
   (installations without their own account: `tail -50 "$(brew --prefix)/var/log/postgresql@16.log"`)
4. Search finds exact words but nothing similar? Then an **embedding model** is missing, see
   [step 8](#8-set-up-the-ai-otherwise-buddy-wont-answer). The error log then shows `Embedding None` or
   `Batch-Embedding fehlgeschlagen`.

**Older installation (before October 2026)?** There the database only started after login. An update (cockpit or
`sudo bash /opt/hydrahive2/installer/update-mac.sh`) switches it over once.

### Update reports "git pull fehlgeschlagen" (git pull failed)
This happens when the version history on GitHub was changed. The fix below discards **only** local changes to the
program code, not your data:

```bash
cd /tmp
sudo -H -u _hydrahive git -C /opt/hydrahive2 fetch origin
sudo -H -u _hydrahive git -C /opt/hydrahive2 reset --hard origin/main
sudo bash /opt/hydrahive2/installer/update-mac.sh
```

For installations without their own account (`HH_SERVICE_ACCOUNT=no`) leave out `sudo -H -u _hydrahive`.

### Installer or add-on module stops with `tapi error` / `unknown architecture`
Apple's command line tools don't match the macOS version. This often happens after a major macOS update. The log
shows something like `ld: tapi error: malformed file … unknown architecture arm64e.x1-macos` or
`clang: error: linker command failed`. Reinstall the tools:

```bash
sudo rm -rf /Library/Developer/CommandLineTools
xcode-select --install
```

Click "Install" in the window, wait, then start the installer or the add-on module again. Tailscale and Voice (on
Apple Silicon) no longer need these tools. The database extension on first install and Voice on Intel Macs are
still built on the Mac.

### Browser still shows the old interface after an update
That's the browser cache. Reload the page with **⌘ + Shift + R**.

**Still stuck?** Ask in the **#⚠️supportforum** on our Discord: <https://discord.gg/GVCZvNxxFA>.
It helps to include the last lines of the error log. **Hide any passwords or keys in it first.**

---

## Uninstalling

```bash
for p in /Library/LaunchDaemons/io.hydrahive.*.plist; do sudo launchctl unload "$p"; done
sudo rm /Library/LaunchDaemons/io.hydrahive.*.plist
rm "$(brew --prefix)/etc/nginx/servers/hydrahive2.conf"
```

HydraHive is now stopped and won't start again. **Your data is still there.** Only the following commands delete it
for good, so back it up first:

```bash
sudo rm -rf /opt/hydrahive2 /opt/hydralink /usr/local/var/hydrahive2 /usr/local/etc/hydrahive2 /usr/local/etc/hydralink
sudo rm -rf /usr/local/lib/hydrahive2
sudo rm -f /usr/local/var/log/hydrahive2*.log /usr/local/var/log/agentlink*.log /usr/local/var/log/nginx-hydrahive*.log
```

`/usr/local/lib/hydrahive2` holds the programs for containers, Tailscale and Voice. Backups from moving to the own
account are under `/usr/local/var/hydrahive2-backup-<date>`. Delete them by hand when you no longer need them.

Finally remove the `_hydrahive` account:

```bash
sudo dscl . -delete /Users/_hydrahive
sudo dscl . -delete /Groups/_hydrahive
```

The programs installed by Homebrew (Python, Node.js, PostgreSQL …) stay installed. You can remove them with
`brew uninstall <name>` if needed.

---

## Summary for AI assistants

> For Claude Code, ChatGPT, Codex & co. asked to set up HydraHive on a Mac. Humans: read above.

**Rules**
- Work as a **normal admin user**. **Never run `install-mac.sh` with `sudo`.** Use `sudo` only where shown below.
- `sudo` asks interactively for the Mac password. **Do not ask the human for the password in chat.** Ask them to type
  it into the terminal themselves, or let them run the commands themselves.
- Do **not** write the HydraHive admin password from the final box into chat, files or commits. Only tell the human
  where it is.
- Run the **check** after every step. If it fails, stop and report the output. Don't guess.

| # | Command | Check (expected) |
|---|---|---|
| 1 | `uname -m; sw_vers -productVersion` | `arm64` and ≥ 13. With `x86_64`: Intel → only continue if `brew --version` already works, otherwise ask the human |
| 2 | `id -Gn \| tr ' ' '\n' \| grep -x admin` | prints `admin` |
| 3 | if `brew` is missing: `xcode-select --install` (GUI) and the official brew.sh script, then `eval "$(/opt/homebrew/bin/brew shellenv zsh)"` + add it to `~/.zprofile` | `brew --version` → `Homebrew 4.x` |
| 4 | `brew install git && sudo mkdir -p /opt/hydrahive2 && sudo chown "$(whoami)" /opt/hydrahive2 && git clone https://github.com/hydrahive/hydrahive2.0.git /opt/hydrahive2` | `test -f /opt/hydrahive2/installer/install-mac.sh && echo ok` |
| 5 | `cd /opt/hydrahive2 && bash installer/install-mac.sh` (takes 15–45 min, asks for the sudo password 1–2×) | green box with `URL` / `Benutzer: admin` / `Passwort` |
| 6 | — | `curl -sk https://localhost/api/health` contains `"status":"ok"` |
| 7 | — | `sudo launchctl list \| grep io.hydrahive` shows `backend`, `nginx`, `postgres`, `agentlink` and `agentlink-frontend` with a PID |
| 8 | — | `"$(brew --prefix postgresql@16)/bin/pg_isready" -h 127.0.0.1` → `accepting connections` |
| 9 | Human: open `https://localhost`, log in as `admin`, change the password at `/profile`, add a provider at `/llm` | Buddy at `/buddy` answers |

**Account:** services run as the hidden system account `_hydrahive` (UID 450–499), which owns code, data and settings;
Homebrew belongs to the human. `git`/`incus` in the HydraHive folder: `cd /tmp && sudo -H -u _hydrahive …`.
`/usr/local/etc/hydrahive2` (incl. `install.conf`) is only readable with `sudo`.
**Paths:** code `/opt/hydrahive2` · AgentLink `/opt/hydralink` · data `/usr/local/var/hydrahive2` ·
settings `/usr/local/etc/hydrahive2` · database `/usr/local/var/hydrahive2/postgres` ·
logs `/usr/local/var/log/hydrahive2*.log` · services `/Library/LaunchDaemons/io.hydrahive.*.plist` ·
backend `127.0.0.1:8001`, AgentLink `127.0.0.1:9000`, nginx `:80`/`:443`.
**Errors:** start with `tail -50 /usr/local/var/log/hydrahive2-error.log`, then [Troubleshooting](#troubleshooting).
The installer can be re-run: brew packages, venv and database that already exist are skipped, the frontend is rebuilt.
