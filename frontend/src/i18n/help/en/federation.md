# Federation

## What is this?

**Federation** connects your HydraHive instance with **other agent systems
(workstations)** via the **A2A protocol** (agent-to-agent). This lets your agent
hand tasks to remote, remotely controlled agent systems — e.g. a specialist on
another machine.

## Core terms

- **Workstation** — another A2A-compatible agent system that you register here.
- **Token** — the **access secret** of the target workstation. No valid token, no
  connection.
- **TLS** — whether the connection is encrypted.

## Step by step

1. **Add** → **Add workstation**.
2. Enter the target workstation's address and **token** (the token comes from the
   other side).
3. Save — registered workstations appear in the list with status ("token
   configured" / "no token", TLS on/off).

## Common questions

- **"No workstations registered yet"** — Normal at the start; begin with **Add your
  first workstation**.
- **"No token"** — The workstation has no valid access secret; without it the
  connection won't work.

## Tips

- **Handle the token securely**: it's the access secret to the other side — like a
  password.
- **Prefer TLS** when the connection runs over a network that isn't fully trusted.

## Federation catalog ("Servers" tab)

See ideas and tasks of several servers in one place. One server is the **hub**, the
others send it their entries (metadata only, the full text is loaded live later).

- **Use as hub** — on the client, turn it on for the partner that should be the hub.
  There is at most one hub, and the pairing must be active.
- **Accept catalog** — on the hub, turn it on for every client whose catalog should
  be accepted.
- A server either acts as hub for others **or** sends to a hub itself, not both.
  Otherwise a message tells you which switch to turn off first.
- **Catalog sync** — sync on/off, interval (60–3600 seconds), which users are sent
  (default: none) and which projects are never sent. Sending runs automatically
  every few minutes and immediately when a sent entry changes.

## Shared task management

Builds on the federation catalog: your own ideas and tasks are shared with the other
paired instances, and their entries show up here for reading. Only **metadata** is
shared (title, status, project, …) — the full text always stays on the instance
where the entry was created and is loaded live when needed. Entries are only
visible under the same username: `till` on this instance only sees entries from
`till` on other instances, nobody else.

Two switches in the "Catalog sync" section control this:

- **"Shared task management"** — shares your own synced entries with the other
  instances **and** shows their entries here. Both directions are tied to one
  switch; there is no separate show-only or share-only option.
- **"Allow editing by other instances"** — can only be turned on once "Shared task
  management" is on. With "Shared task management" alone, your own entries are only
  **visible** elsewhere, not editable. This switch only takes effect from the
  editing stage onward — until then it changes nothing yet.

## "Catalog" tab

Shows the copy of other instances' entries, **read only**. Columns: kind
(task/idea), short ID, title, status, project, instance, last updated. Filter by
instance, project, status and kind, plus a search field. Without "Shared task
management" turned on or without a hub set, the list stays empty.

### Project mapping

Entries from other instances appear in your own project that has **the same name** as
the project at the origin (case and surrounding spaces do not matter), as long as you
are a member there. The "Project mapping" table below the list shows every origin
project with instance, number of entries, mapping and note. You can change the
mapping per row:

- **Automatic (same name)** — the default rule.
- **Project …** — a specific project of yours, even with a different name.
- **Do not show** — the entries no longer appear in any project list, only in the
  catalog.

The mapping applies **only to you**; every user sets it up themselves, admin rights
are not needed. Notes: "Ambiguous" (several projects with that name), "No project
with the same name", "Not a member" (the project exists but you are not on it),
"Target not available" (the chosen project is gone or you are no longer a member).

### Not assigned

Origin projects without a matching project of yours are listed under "Not assigned",
grouped by instance. Their entries appear in no project list until you pick a project
above. For "No project with the same name", an **admin** can click **"Create project
here"** to create an empty project with that name (member: the signed-in user).
Nothing is copied from the origin project — no files, no members. After that the
automatic mapping takes over. Other users see the note "An admin can create the
project here". Projects themselves are never synced or created automatically.
