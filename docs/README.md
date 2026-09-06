# HydraHive documentation

This directory contains product, operator, architecture, security and implementation documentation for HydraHive.

> **Start here:** [FEATURES.md](FEATURES.md) is the code-backed inventory of the current product. `SPEC.md` remains the binding product baseline, while files under `specs/`, `plans/` and `audit/` can describe a point-in-time design or investigation.

## Current product documentation

| Document | Audience | Purpose |
|---|---|---|
| [../README.md](../README.md) | Everyone | Product overview, quick start, security summary and repository map |
| [FEATURES.md](FEATURES.md) | Users, operators, contributors | Current implemented feature inventory, requirements and boundaries |
| [USER_GUIDE.md](USER_GUIDE.md) | Users and administrators | Day-to-day use of chat, agents, projects, modules and operations |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Contributors and operators | Runtime architecture, data flow, storage and extension model |
| [SECURITY_THREAT_MODEL.md](SECURITY_THREAT_MODEL.md) | Operators and reviewers | Assets, trust boundaries, controls and residual risks |
| [RELEASE_NOTES.md](RELEASE_NOTES.md) | Users and operators | Current unreleased changes and published-release pointer |
| [COCKPITS.md](COCKPITS.md) | Users and UI contributors | Navigation and cockpit map |
| [../SPEC.md](../SPEC.md) | Maintainers and contributors | Binding product baseline; updates require maintainer approval |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | Contributors | Git workflow, checks and code conventions |
| [../SECURITY.md](../SECURITY.md) | Security reporters | Vulnerability reporting and supported versions |

## Architecture deep dives

The subsystem documents in [`architecture/`](architecture/) complement the high-level architecture. When an older deep dive conflicts with current code or [FEATURES.md](FEATURES.md), verify against the implementation before relying on it.

- [Architecture index](architecture/README.md)
- [Authentication](architecture/auth.md)
- [Runner](architecture/runner.md)
- [Tools](architecture/tools.md)
- [Memory](architecture/memory.md)
- [Context compaction](architecture/compaction.md)
- [Media-model integration](architecture/media-models.md)

## Operations and deployment

- [Installer guide](../installer/README.md)
- [Compute-node runbook](compute-node-runbook.md)
- [Ubuntu 26.04 upgrade runbook](ubuntu-2604-upgrade-runbook.md)
- [Ollama provider guide](ollama-provider.md)
- [Node-agent reference](../node-agent/README.md)
- [Module hub](https://github.com/hydrahive/hydrahive2-modules)

## Security

- [Threat model](SECURITY_THREAT_MODEL.md)
- [Security hardening notes](security-hardening.md)
- [Dependency audit, August 2026](security-dependency-audit-2026-08.md)
- [Security policy](../SECURITY.md)

Security audits are date-stamped snapshots. Re-run the documented checks before treating their findings as current.

## Design records and historical documents

### `specs/`

Feature-level design documents, acceptance criteria and implementation contracts. Their filenames identify the subsystem, but not every document is a live product manual. Use them to understand why a feature was designed a certain way; use [FEATURES.md](FEATURES.md) and the code to determine what is currently present.

See [specs/README.md](specs/README.md).

### `plans/`

Implementation plans used while building or changing a feature. A completed plan is historical evidence, not a guarantee that later refactors preserved every path or name.

### `audit/`

Point-in-time implementation and gap audits. The date in the filename is part of the result and should be cited when referencing it.

### `compute-roadmap.md`

Forward-looking planning for the compute subsystem. It should not be read as an implemented-feature list.

## Documentation rules

When changing HydraHive:

1. update [FEATURES.md](FEATURES.md) for a new or removed user-visible capability;
2. update [USER_GUIDE.md](USER_GUIDE.md) for changed user/admin workflows;
3. update [ARCHITECTURE.md](ARCHITECTURE.md) or the relevant `architecture/` deep dive when components or data flow change;
4. update [COCKPITS.md](COCKPITS.md) when navigation changes;
5. modify `SPEC.md` only with explicit maintainer approval and in a standalone commit;
6. label external dependencies, required credentials and infrastructure limitations explicitly;
7. do not describe planned work as implemented.

Repository conventions are defined in [CONTRIBUTING.md](../CONTRIBUTING.md).
