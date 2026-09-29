# Access and groups

## What is this?

**Access grants** decide **who may use which feature**. **Groups** bundle
users, for example “Family” or “Dev team”. A grant to a group applies to all
of its members.

Only **admins** manage access. Admins themselves may always do everything.

## Which features are protected?

Only features that are explicitly declared as protected. Everything else stays
open to all users. After the update these features are **admin-only** until
you grant them:

- **VMs** and **containers**
- **Federation** (remote-controlling workstations)
- **Home Assistant: switch devices** (viewing stays open to everyone)
- **Voice**, **Archiver**, **OpenTor**

A one-time notice in the admin cockpit reminds you of this.

## Step by step

### Create a group
1. Open **Admin → Users**.
2. In the **Groups** section enter a name and click **Create**.
3. Add members via **Add member**.

### Grant a feature
1. Open **Admin → Access**.
2. Each row in the table is a feature. The columns are **Everyone**, your
   groups and individual users.
3. Click a cell to switch between **–**, **use** and **manage**.

Changes apply immediately, no restart needed.

## Good to know

- **Agents inherit their owner’s rights.** If a user may not switch devices,
  their buddy does not get that tool either. The agent editor greys such tools
  out.
- Without access the menu entry disappears. Opening the address directly shows
  “No access”.
- Deleting a group removes its grants. Deleting a user removes their
  memberships and grants.
- Every change is logged.
- Under **Profile → My access** every user sees what they may do.
