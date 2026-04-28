# Projects

## What is this?

A project is the middle tier of the **3-tier architecture**: master delegates to projects, projects use specialists. It's a combination of:

- **Workspace** — its own filesystem folder (`data/workspaces/projects/<id>/`)
- **Project agent** — auto-created, bound to the workspace, can't operate outside
- **Members** — users with access

A project = a bounded work context. Example: your "Website XY" effort gets a project with its own git repo, memory, and sessions.

## What can I do here?

- **Create a new project** — name, description, members, model for the project agent, optional `git init`
- **Add / remove members** via chips in the detail
- **Set status** — active / archived
- **Delete** — wipes everything (project agent + workspace + all sessions)
- **Sessions** in this project: via Chat tab "Projects"

## Key terms

- **Project agent** — agent of type `project`, paired with this project
- **Workspace** — assigned filesystem area, isolated from other projects
- **Member** — user with access. Admin sees all projects.

## Step by step

### Create a project for a code effort

1. Click **+ New**
2. Name: e.g. *Website-Relaunch*, description: short explanation
3. Members: yourself (or multiple users)
4. Model: `claude-sonnet-4-6`
5. Check **Initialize workspace with `git init`** — version-controllable from the start
6. **Create** — project agent is created, workspace exists empty

### Load code into the workspace

The workspace is at `data/workspaces/projects/<project_id>/`. Three options:

```bash
# Option 1: symlink existing code
ln -s /path/to/your/code/* /home/till/.hh2-dev/data/workspaces/projects/<id>/

# Option 2: copy
cp -r /path/to/your/code/* /home/till/.hh2-dev/data/workspaces/projects/<id>/

# Option 3: git clone
cd /home/till/.hh2-dev/data/workspaces/projects/<id>/
git clone <repo-url> .
```

### Start a project chat

1. Open **Chat** in the sidebar
2. **+ New** → mode **In project**
3. Pick the project — project agent is automatically attached
4. Tools like `file_read`, `shell_exec` now operate inside the project workspace

### Remove a member

1. Open the project
2. In the members area click `×` next to the user chip
3. Confirm

## Common errors

- **`User does not exist`** when adding a member — user must be created first (System page → Users, or via backend).
- **Project agent orphaned** if the project agent is deleted directly instead of the project — project shows the agent missing. Fix: delete the project or recreate the agent via the Agents page with `project_id`.

## Tips

- **One project per major effort** — clean separation, separate history, separate memory
- **Reduce members to who really works on it** — sessions are visible to all members
- **Optional `git init`** even if you don't push remotely — local versioning helps roll back when the agent breaks something
