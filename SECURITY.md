# Security policy

HydraHive can execute agent tools, install services and manage infrastructure. Security reports must therefore be handled privately until a fix is available.

## Reporting a vulnerability

Do **not** open a public issue containing exploit details, credentials, personal data or a working proof of concept.

Use the repository host's private vulnerability-reporting function when it is available. If no private reporting function is shown, contact a project maintainer through an already established private project channel and ask for a secure reporting path before sending details.

Include:

- affected version, release or commit;
- deployment type and relevant optional components;
- reproducible steps;
- expected and actual security boundary;
- impact and preconditions;
- minimal logs or proof of concept with all secrets and personal data removed;
- whether the issue appears to be actively exploited.

The project does not publish a guaranteed response or remediation SLA in this repository. Do not assume a report was received until a maintainer acknowledges it.

## Supported versions

HydraHive is currently beta and this repository does not define a multi-version security-support matrix. Security fixes are developed against the current maintained branch. Operators should review release notes, back up data and update promptly after a fix is published.

## Security scope

Particularly relevant reports include:

- authentication or authorization bypass;
- cross-user or cross-project data access;
- credential, token or private-key disclosure;
- remote code execution outside an explicitly authorized tool/extension action;
- confirmation-gate bypass;
- path traversal or workspace escape;
- server-side request forgery that bypasses documented URL/credential constraints;
- malicious module/plugin/extension escalation beyond its documented trust boundary;
- compute-node enrollment, certificate or command-channel compromise;
- stored or reflected browser injection;
- unsafe file upload or media processing.

The following are not automatically vulnerabilities, but documentation or hardening reports are still welcome:

- an administrator deliberately running a reviewed extension installer, which is privileged by design;
- an agent executing a tool that an authorized user explicitly assigned and confirmed;
- prompts or attachments being sent to the cloud provider selected by the user;
- lack of trust for the default self-signed development/installation certificate;
- a malicious locally installed plugin executing within the privileges documented for plugins.

A behavior can still be a vulnerability if it crosses the documented permission, confirmation, ownership or isolation boundary.

## Operator guidance

- Keep the FastAPI backend bound to loopback behind the configured reverse proxy.
- Replace or explicitly trust the default self-signed certificate according to the deployment environment.
- Use unique secrets and rotate exposed credentials immediately.
- Grant admin rights, tools, plugins and extension installation access only when necessary.
- Review third-party module/plugin/extension code before installation.
- Keep backups of `HH_DATA_DIR`, `/etc/hydrahive2` and external service data.
- Treat cloud providers, MCP servers and external integrations as separate data processors/trust domains.

See [docs/SECURITY_THREAT_MODEL.md](docs/SECURITY_THREAT_MODEL.md) for the architecture-level threat model.
