# Plugins

## What is this?

**Plugins** extend HydraHive with additional **tools/functions** for the agents.
Unlike modules (which bring their own pages), plugins mostly add functionality in
the background. You install them from a **hub** and manage them here.

## The two tabs

- **Hub** — the catalog of available plugins. You **install** from here.
- **Installed** — your active plugins with status (**loaded** or **error**).

## Step by step

1. Open the **Hub** tab → pick a plugin → **Install**.
2. Under **Installed** you see the status.
3. As needed, **Update**, **Reinstall**, or **Remove**.

## Common questions

- **"No plugins found in the hub"** — The hub index couldn't be loaded
  (network/source); try again later.
- **"Error" instead of "loaded"** — The plugin failed to start. **Reinstall** or
  check the plugin log.

## Plugin vs. module vs. extension

- **Plugin** — extends **agent tools/functions** (usually no own page).
- **Module** — brings its **own page/feature** into HydraHive (e.g. Atelier).
- **Extension** — external add-on services/integrations (separate area).

## Tips

- **Only install what you need** — every active plugin is surface for problems;
  less is easier to maintain.
