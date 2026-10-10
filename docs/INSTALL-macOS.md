# Installing HydraHive on a Mac – step by step

> **Status: experimental.** HydraHive runs on macOS (last tested on 1 October 2026 on an Intel iMac with macOS 15).
> The Mac installer is simpler than the Linux installer, though: some features are not available on a Mac (see
> [What does not work on a Mac](#what-does-not-work-on-a-mac)). For a server that runs around the clock we recommend
> Linux (Ubuntu).

Deutsche Fassung: [INSTALL-macOS.de.md](INSTALL-macOS.de.md)

---

## At a glance

| | |
|---|---|
| **Time** | about 20–40 minutes (mostly downloads) |
| **Difficulty** | You type a few commands into **Terminal**. Every command below is ready to copy. |
| **Afterwards** | HydraHive runs in the background and starts automatically when the Mac boots. You open it in your browser. |

---

## 1. What you need

| | Minimum | Recommended |
|---|---|---|
| **Mac** | Intel or Apple Silicon (M1–M5) | Apple Silicon |
| **macOS** | 13 (Ventura) | 15 (Sequoia) or newer |
| **Memory** | 8 GB | 16 GB or more (with local AI models: 32 GB+) |
| **Free disk space** | 10 GB | 30 GB+ (database, media, local models) |
| **User account** | an account with **administrator rights** (you must be able to enter your Mac password for `sudo`) | |
| **Internet** | during installation | |

> **About macOS versions:** Homebrew (see step 3) officially supports macOS 15 and newer on Apple Silicon. Older
> versions and Intel Macs are "not officially supported" by Homebrew but usually work. So far we have tested HydraHive
> on an **Intel iMac with macOS 15.3**.

**For the AI itself** (set up after installation, step 9) you also need one of these:
- an **API key** from an AI provider (e.g. Anthropic, OpenAI, OpenRouter) **or** a login with a ChatGPT/Claude
  subscription, **or**
- **Ollama** for local models directly on the Mac (free, but needs a lot of memory).

---

## 2. Open Terminal

1. Press **⌘ + Space** (Spotlight).
2. Type **Terminal** and press **Return**.

A window with text opens. This is where you paste the commands: copy, click into Terminal, **⌘ + V**, **Return**.

> **Entering your password:** When Terminal shows `Password:`, type your **Mac password**. **No characters appear**
> while you type – that is normal. Just type and press Return.

---

## 3. Install the developer tools and Homebrew

**Homebrew** is a program that installs other programs (Python, Node.js, a database …). The HydraHive installer needs it.

**3a. Apple developer tools** (if not installed yet):

```bash
xcode-select --install
```

A window opens → click **Install** and wait (a few minutes).
If it says "already installed", you're set – continue with 3b.

**3b. Install Homebrew** (command from [brew.sh](https://brew.sh)):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

The installer asks for your password and shows what it is going to do – confirm with **Return**.

**3c. Important – set Homebrew up permanently.** At the end Homebrew shows two commands under **"Next steps"**.
Run **exactly those**. They look like this:

- **Apple Silicon (M1–M5):**
  ```bash
  echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
  eval "$(/opt/homebrew/bin/brew shellenv)"
  ```
- **Intel Mac:**
  ```bash
  echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
  eval "$(/usr/local/bin/brew shellenv)"
  ```

**Check:**

```bash
brew --version
```

You see a version number (e.g. `Homebrew 4.x.x`)? → Continue.
`command not found`? → Repeat step 3c, then close and reopen Terminal.

---

## 4. Download HydraHive

HydraHive goes into **`/opt/hydrahive2`** (that is where the installer looks).

```bash
brew install git
sudo mkdir -p /opt/hydrahive2
sudo chown "$(whoami)" /opt/hydrahive2
git clone https://github.com/hydrahive/hydrahive2.0.git /opt/hydrahive2
cd /opt/hydrahive2
```

> Want a different folder? Set `export HH_REPO_DIR=/your/path` before running the installer. For beginners:
> just keep `/opt/hydrahive2`.

---

## 5. Run the installer

```bash
cd /opt/hydrahive2
bash installer/install-mac.sh
```

**Important:** do **not** start it with `sudo`. The installer asks for your password itself when it needs it.

### What the installer does (takes 10–30 minutes)

| Phase | What happens |
|---|---|
| 1 | Installs via Homebrew: Python 3.12, Node.js, git, ffmpeg, GitHub CLI, plus `uv` and `mmx-cli` |
| 2 | Creates the folders: data in `/usr/local/var/hydrahive2`, settings in `/usr/local/etc/hydrahive2` |
| 3 | Sets up the backend (Python environment) |
| 4 | Builds the web interface (takes the longest) |
| 5 | Installs the PostgreSQL 16 database with pgvector (for data mining/memory) |
| 6 | Sets HydraHive up as a **background service** (starts automatically at boot) |
| 7 | Sets up the **nginx** web server with HTTPS (self-signed certificate) |

At the end a green box appears:

```
HydraHive2 — Installation fertig (Mac)
  URL:       https://192.168.x.x
  Benutzer:  admin
  Passwort:  <random password>
```

(The box is in German: *Benutzer* = user, *Passwort* = password.)

> ### ⚠️ Write the password down right away!
> It is shown **only once**. If you see `(siehe: log show --process uvicorn)` instead of a password, see
> [Troubleshooting → Admin password](#admin-password-not-shown).

---

## 6. Open HydraHive in your browser

- **On the same Mac:** <https://localhost>
- **From another device on your home network** (phone, laptop): the **URL from the green box**, e.g. `https://192.168.1.50`

### The security warning is expected
HydraHive creates its own certificate. Your browser doesn't know it and warns you:

- **Safari:** "Show Details" → "visit this website" → confirm
- **Chrome:** "Advanced" → "Proceed to … (unsafe)"
- **Firefox:** "Advanced…" → "Accept the Risk and Continue"

You only need to do this the first time.

---

## 7. Log in and change the password

1. Log in with **admin** and the password from step 5.
2. **Set your own password right away** (in your profile or user management).

---

## 8. Check that everything is running

```bash
sudo launchctl list | grep io.hydrahive
```

You should see entries for **`io.hydrahive.backend`** and **`io.hydrahive.nginx`**.

```bash
curl -sk https://localhost/api/health
```

Expected: a line containing `"status":"ok"`.

---

## 9. Set up the AI (otherwise Buddy won't answer)

After installation **no AI model** is configured yet. In the cockpit:

**Settings → AI models** (German UI: *Einstellungen → KI-Modelle*), then one of:

| Option | For whom | Note |
|---|---|---|
| **API key** (Anthropic, OpenAI, OpenRouter, NVIDIA …) | fastest start | costs depend on usage |
| **Login with a ChatGPT or Claude subscription** | if you already have one | |
| **Ollama (local)** | privacy, offline | needs a lot of memory; see below |

> If new models don't appear in the picker after logging in: restart the service once (see
> [Useful commands](#useful-commands)).

### Optional: local models with Ollama
1. Install Ollama: `brew install ollama` (or the app from [ollama.com](https://ollama.com))
2. Start it: `brew services start ollama`
3. Pull a model, e.g. `ollama pull qwen3:8b` (pick a model size that fits your memory)
4. In HydraHive under **Settings → AI models**, add an Ollama provider with the address `http://localhost:11434`.

Details: [docs/ollama-provider.md](ollama-provider.md)

---

## What does not work on a Mac

The Mac installer only sets up the **core**. The following is **not** available on a Mac (or only manually):

| Feature | On a Mac | Why |
|---|---|---|
| **VMs & containers** (libvirt/QEMU, Incus) | ❌ not available | Linux only |
| **Voice / speech recognition service** (Whisper container) | ❌ not automatic | runs in an Incus container on Linux |
| **WhatsApp connection** | ❌ not set up | the bridge is only installed by the Linux installer |
| **Samba shares** (project folders on the network) | ❌ not available | Linux module |
| **Tailscale remote access** | ⚠️ not automatic | install the Tailscale app for macOS yourself |
| **Web search (SearXNG)** | ⚠️ not automatic | enter your own SearXNG address in the settings, otherwise the `web_search` tool won't work |
| **Starter agents & MCP servers** | ⚠️ not automatic | Linux creates them during install; on a Mac create them manually in the cockpit |
| **Local media models** (image/video on an NVIDIA GPU) | ❌ not available | needs NVIDIA + Docker |
| **Extensions** (Settings → Extensions) | ⚠️ mostly not | many need `apt`/`docker` and fail with an unclear error message |
| **Modules** (Settings → Modules) | ✅ almost all | 21 of 22 tested; **OpenTor** does not work (Tor only via Linux packages) |
| **Firewall rules** (ufw) | ❌ | macOS has its own firewall |

**What works well:** the cockpit, Buddy, agents, projects, workshop, data mining/memory, tasks, modules such as
Atelier, Storyteller, household budget, etc., and updates from the cockpit.

---

## Things to watch out for

- **The Mac must stay awake.** HydraHive only runs while the Mac is on and **not asleep**. For continuous operation:
  **System Settings → Energy** (or "Battery" → "Options") → prevent sleep, keep a laptop plugged in.
- **Ports 80 and 443** are used by HydraHive (nginx). If another web server already runs on the Mac, they will clash.
- **Access from the network:** other devices reach HydraHive via the Mac's IP address. If the address changes (e.g. a
  different Wi-Fi), the certificate no longer fully matches and the browser warning returns.
- **macOS firewall:** if it is on, macOS asks on first start whether nginx may accept connections → **Allow**.
- **Never `sudo bash installer/install-mac.sh`** – always run it as a normal user.
- **Backups:** your data lives in `/usr/local/var/hydrahive2`, the settings (including keys) in
  `/usr/local/etc/hydrahive2`. Back up these two folders. Time Machine includes them.

---

## Useful commands

| What | Command |
|---|---|
| Restart the service | `sudo launchctl kickstart -k system/io.hydrahive.backend` |
| Is the service running? | `sudo launchctl list \| grep io.hydrahive` |
| Error log | `tail -50 /usr/local/var/log/hydrahive2-error.log` |
| Update log | `tail -50 /usr/local/var/log/hydrahive2-update.log` |
| Web server errors | `tail -50 /usr/local/var/log/nginx-hydrahive-error.log` |

### Updates
Easiest via the update function in the cockpit. Manually:

```bash
eval "$(brew shellenv)"
bash /opt/hydrahive2/installer/update-mac.sh
```

---

## Troubleshooting

### `brew: command not found`
Homebrew isn't on your path → run step 3c, close and reopen Terminal.

### `node`, `npm` or `python3.12` "command not found" during an update
Same cause. Run `eval "$(brew shellenv)"` before the update (already included in the update command above).

### Admin password not shown
On first start the password is written once to the log and to a file:

```bash
sudo cat /usr/local/etc/hydrahive2/.admin_initial_password
```

If the file no longer exists, search the system log:

```bash
log show --predicate 'process == "uvicorn"' --last 1h | grep "Passwort:"
```

### Installer stops at `npm install` ("network", "ECONNRESET")
Usually a short network hiccup during download. Simply **run the installer again** – it continues where it left off
(finished steps are skipped).

### Update reports "git pull fehlgeschlagen" (git pull failed)
This happens when the version history on GitHub has changed. Fix (discards **only** local changes to the program code,
not your data):

```bash
cd /opt/hydrahive2
git fetch origin
git reset --hard origin/main
bash installer/update-mac.sh
```

### Browser still shows the old interface after an update
Browser cache. Reload the page with **⌘ + Shift + R**.

### The page doesn't load at all
1. Is the service running? → `sudo launchctl list | grep io.hydrahive`
2. Check the error log → `tail -50 /usr/local/var/log/hydrahive2-error.log`
3. Restart the service → `sudo launchctl kickstart -k system/io.hydrahive.backend`

Still stuck? Ask in **#⚠️supportforum** on our Discord: <https://discord.gg/GVCZvNxxFA> – ideally with the last lines
of the error log (blank out any passwords/keys first).
