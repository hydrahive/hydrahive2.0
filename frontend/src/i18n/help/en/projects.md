# Project Cockpit

## What is a project?

A project is a bounded work context with its own workspace, project agent, members, sessions, and optional Git, server, and network connections. The project agent only operates inside its assigned workspace.

## Layout

- **Center:** project-bound chat
- **Left:** project selection, project actions, agents, Git status, and AI settings
- **Right:** Git tree, workspace files, and tasks

The active project is stored server-side as a user preference.

## Select a project and find its actions

1. Expand the **Project** panel on the left.
2. Select a project.
3. Project actions appear below the selector and description.

When the panel is collapsed, its actions are hidden too. Project-specific actions deliberately do not live in the global top bar.

### Direct actions

- **+ New project** — create a project and its project agent
- **Edit** — change name, description, status, and notes; delete the project with confirmation

### Manage

- **Access** — manage members and specialists
- **Servers** — assign or remove servers, VMs, and containers
- **Mounts** — create and assign SMB/network shares
- **Git** — initialize or clone repositories, commit, configure remotes, pull, and push
- **Integrations** — MCP server IDs, allowed plugins, project LLM key, and Samba

### Insights

- **Statistics** — sessions, messages, tokens, and last activity
- **Sessions** — complete project session list; clicking opens the workshop
- **Audit** — filter project activity by action and user

## Global top bar

The top bar is reserved for global functions:

- Switch between Projects, Buddy, Media, Vault, and Admin
- **Apps** opens all areas allowed for your role
- **Help** opens this contextual help
- The user menu opens Profile and Settings or signs you out

On small displays, navigation appears in a right-side drawer.

## Security

- Delete and remove operations require confirmation.
- Stored Git tokens are never displayed.
- An existing project LLM key is not loaded into the form; it can only be replaced or explicitly removed.
- The Samba password is neither displayed nor copyable in the Project Cockpit.
- Members only see projects they can access; admins see all projects.

## Common issues

- **Project actions are missing:** expand the **Project** panel on the left.
- **A user cannot be added:** create the account in user administration first.
- **Pull/Push is disabled:** the repository needs a remote; push is disabled when there are no outgoing commits.
- **A mount or server is missing:** only available resources allowed for your account are listed.

## Tip

Use one project per major effort. This keeps workspace, agent, sessions, Git history, and access rights cleanly separated.
