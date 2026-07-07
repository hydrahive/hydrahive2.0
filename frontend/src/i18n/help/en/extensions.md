# Extensions

## What is this?

**Extensions** are **external add-on services** that expand HydraHive with larger
capabilities — e.g. a Matrix server for team chat or other integrations. They run
as their own service, either **natively** on the server or in **Docker**.

## What can I do here?

- Browse available extensions by **category** (installed / not installed).
- **Install**, **uninstall**, or (if it has a UI) **open** an extension.
- See the **status**: Not installed / Active / running-but-unreachable.

## Native vs. Docker

- **Native** — the service runs directly on the server.
- **Docker** — the service runs in a container. This requires **Docker to be
  available** (the page shows whether Docker is installed).

## Step by step

1. Pick an extension.
2. **Install** (for Docker extensions, Docker must be present).
3. After installation the status shows **Active**; if the extension has a UI, you
   can **Open** it.

## Common questions

- **"Docker is not installed"** — For Docker-based extensions, Docker must be set
  up on the server first.
- **"running but unreachable"** — The service starts but isn't reachable (yet);
  wait a moment or check the extension log.

## How it differs

- **Extension** — external **service/integration** (native or Docker).
- **Plugin** — agent **tools** in the background.
- **Module** — a **page/feature** in HydraHive.

## Tips

- **Install only when needed** — every running service uses resources.
