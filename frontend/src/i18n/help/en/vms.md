# Virtual Machines (VMs)

## What is this?

Here you run **full virtual computers** directly on the HydraHive server — real
operating systems (Linux, Windows …) in an isolated environment. Technically this
uses **QEMU/KVM** (Linux's native virtualization). You see all VMs as cards, can
start/stop them, and log in via a **VNC console right in the browser** — like a
monitor plugged into the VM.

Think of a VM as a **computer inside the computer**: its own disk, its own OS, its
own network — fully separated from the host.

## What is it good for?

- Set up a **test system** without real hardware.
- Try a **different operating system** (e.g. Windows on a Linux server).
- Run a service **in isolation** so it can't touch the main system.
- Import an existing disk image (`qcow2`) and keep running it.

## Core terms

- **ISO** — an installation image (e.g. the Windows or Ubuntu installer). You
  upload it once into the **ISO library** and boot new VMs from it.
- **Disk / qcow2** — the VM's virtual hard drive.
- **Snapshot** — a frozen state of the VM you can return to later (handy before
  risky changes).
- **Bridged / Isolated** — the network mode (see below).
- **VNC console** — the VM's screen, usable in the browser.

## Step by step: create your first VM

1. **Upload an ISO first**: open the **ISO library** and upload your operating
   system's installation image (the tip at the top of the page points to this).
2. Click **New VM**.
3. Give it a **name** (1–32 chars, starts with a letter, only `a-z A-Z 0-9 -`).
4. Choose the **boot source**:
   - **Boot from ISO** — new blank disk + the ISO as install medium (the normal
     case for a fresh install).
   - **Imported disk** — take over an existing `qcow2` from a disk import.
   - **Blank disk** — boots into nothing until you supply a system later.
5. Choose the **network**:
   - **Bridged (br0)** — the VM gets its own IP from your LAN (like a real device).
   - **Isolated** — no network access (maximally sealed off).
6. Optionally adjust **disk interface / machine type / network device** (defaults
   usually fit; `virtio` = fastest under KVM, `sata` = more compatible for older
   guests).
7. **Create VM**.
8. Click **Start** → then **Console** to install/operate the OS in the browser.

## The actions on each VM

- **Start** — power up the VM.
- **Console** — open the VNC screen in the browser.
- **Stop** — clean shutdown (ACPI, like the "shut down" button).
- **Power off** — hard off (SIGKILL, like pulling the plug — only when needed).
- **Snapshots** — save/restore states.
- **QEMU log** — technical log (helps with boot problems).
- **Edit / Delete**.

## Common mistakes

- **"No ISOs available"** — Upload an installation image into the ISO library
  first, then create the VM.
- **VM won't start / boots into nothing** — With "blank disk" there's no system;
  boot from an ISO or use an imported disk. The QEMU log gives hints.
- **No network in the VM** — Network is set to **Isolated**; switch to **Bridged**
  if the VM should reach the network.
- **Console stays black** — VM may not be running yet or already shut down; check
  the card's status.

## Tips

- **Snapshot before risk**: take a snapshot before updates or experiments —
  returning is one click.
- **Prefer virtio** when the guest OS supports it (Linux always, Windows with a
  driver) — noticeably faster.
- **Shut down cleanly** (Stop/ACPI) rather than "Power off", so the guest file
  system doesn't get damaged.
