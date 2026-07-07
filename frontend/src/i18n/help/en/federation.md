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
