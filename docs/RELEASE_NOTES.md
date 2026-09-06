# Release notes

## Unreleased — current `main` after v2.0.0

These notes summarize the repository state at commit `05cdf4f6` on 2026-09-06. They are not a published GitHub release. The comparison range `v2.0.0..05cdf4f6` contains **176 commits**, calculated with:

```bash
git rev-list --count v2.0.0..05cdf4f6
```

### Local model and media stack

- Added Ollama as a managed provider, including live catalog, model lifecycle, context/tool handling and optional `llmfit` hardware guidance (#370–#372, #407–#409).
- Added configurable video backends and ComfyUI integration (#375–#377, #385).
- Added automated local image/video provisioning with SDXL and Wan workflows, model switching and start/end-frame image-to-video support (#412, #417, #418, #421).
- Adjusted the SDXL workflow for 16 GB GPUs to use ComfyUI `--novram` (#420).
- Model selection now exposes provider and cost status, while embedding selection uses the live catalog (#410, #411).

### Compute nodes and infrastructure

- Added the compute-node foundation, certificate enrollment, command/job channel and remote container placement (#362–#365).
- Added node setup workflows, including Incus-oriented provisioning (#367, #368).
- Added Ubuntu 26.04 images and a guarded Ubuntu 24.04 → 26.04 upgrade/repair path (#374, #400, #405).
- Preserved `/tmp` mounts declared in `/etc/fstab` instead of masking them during host repair (`4b28774e`, `b0567995`).

### Chat, agents and projects

- Decoupled server-side runs from the browser request, added run reattachment and made Stop survive a page reload (#388, #389).
- Added project-member roles and the corresponding audit action (#390).
- Added independent cockpit sessions per agent and fixed persistence/race issues around agent/session selection (#391, #394, #395).
- Fixed loading older messages in the cockpit and sanitized foreign Anthropic blocks in resumed conversations (#392, #393).
- Added stable user principals for newer ownership-sensitive resources (#361).
- Added tool-context fields for the current user input and turn ID (#379, #380).
- Added a capability gate so models without tool support do not receive tool schemas (#384).

### Cockpit and frontend

- Consolidated Admin functions into docked cockpit overlays for users, modules, plugins, credentials, themes, MCP, models, extensions, system, settings, containers and VMs (#345–#359).
- Added module tabs and bare cockpit chrome (#343).
- Added Buddy idle/working/action-video states and Buddy settings in the cockpit (#338–#340, #382).
- Enabled stricter TypeScript checks and ESLint in CI (#335, #336).
- Made the frontend generator skip/remove rebuildable module copies with missing local dependencies instead of breaking the whole UI (#415, #416).

### Modules, installer and operations

- Module installation now resolves declared dependencies before the frontend build (#414).
- Module update streams finish before restart and report stream errors to the caller (#413, #419).
- Pinned Python dependency ranges and added an informative `pip-audit` CI step after the LiteLLM supply-chain incident (#399).
- Pinned npm 11 for service users and made the voice bridge dependency survive updates (#401, #402).
- Synchronized the Playwright browser after updates and hardened streaming downloads against SQLite lock contention (#403, #404).

### Memory, analytics and reliability

- Added measured model-speed data to token auditing (#396).
- Changed memory recall so unsupported memories are not preferentially injected (#397).
- Added a repository index over the numbered specification set (#398).
- Made previously silent runner failures and exception paths visible (#333, #334).
- Fixed partial model-registry cache behavior and the Nemotron Ultra context-window metadata (#373, #378).

### Documentation in this update

- Replaced the root README with an installation-, security- and architecture-aware product overview.
- Added a code-backed feature inventory, including all **18** official hub manifests and **32** core service-extension manifests.
- Reworked the architecture and user guides around the current cockpit, modules, compute, media and memory implementation.
- Added a security policy and threat model with explicit trust boundaries and residual risks.
- Added/upgraded frontend and installer contributor/operator guides.

### Upgrade notes

- Back up `HH_DATA_DIR`, `HH_CONFIG_DIR` and separately managed extension data before upgrading.
- Module updates can install dependencies, rebuild the frontend and request a backend restart.
- The Ubuntu 26.04 path is host-affecting; read `installer/README.md` and the related runbooks before opting in.
- Local media provisioning downloads large third-party model files and requires compatible NVIDIA/CUDA + Docker infrastructure.
- Existing installs should review provider/model assignments after enabling Ollama or local media models.

---

## v2.0.0 — 2026-07-13

The first GitHub release marked as production established the HydraHive 2.0 baseline with the code graph, Media/Video editor, cockpit redesigns and chat/model fixes.

Canonical release entry: <https://github.com/hydrahive/hydrahive2.0/releases/tag/v2.0.0>

The original release page records its point-in-time verification numbers. Those numbers describe the tagged release and are not reused here as claims about current `main`; current verification must be run again for each change set.
