# Home Assistant

## What is this?

This module connects your **Home Assistant smart home** to HydraHive: you see your
**devices** (lights, switches, sensors, thermostats …) and can **switch them
directly** — without opening the Home Assistant app. Your agent can control
devices through it too.

## What can I do here?

- **See devices**: all entities with their current state.
- **Switch**: lights on/off, toggle switches, trigger scenes, etc.
- **Search**: filter by name or `entity_id` via the search field.
- **Favorites**: mark frequently used devices and show them via **Favorites only**.
- **Refresh**: reload the current state.

## Prerequisite

A **connection to your Home Assistant server** must be set up (address + access
token). Without it, no devices appear. The connection is configured in the
system/connection settings.

## Common questions

- **"No matching devices found"** — Either the connection isn't set up, or the
  search term matches no device. Clear the search field and **Refresh**.
- **"Switching doesn't react"** — Check that Home Assistant is reachable and the
  entity is actually switchable (sensors only display, they don't switch).

## Tips

- **Set favorites** for the devices you use daily — saves searching.
- **Remember the entity_id**: the exact `entity_id` finds a device fastest (even
  when the display name is ambiguous).
