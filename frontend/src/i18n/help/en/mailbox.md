# Mailbox

## What is it?

**Mailbox** is HydraHive's webmail and mail archive. You can read and use several
IMAP/SMTP accounts. Every synchronized message is also archived locally as an
`.eml` file. If a message is later deleted from the mail server, the archived
copy remains available under **Archive only**.

## Add an account

1. Open **Mailbox** and click **Add account** on the left.
2. Enter the mail address. Mailbox suggests server settings for known providers.
3. Choose the sign-in method:
   - **Password** for regular IMAP/SMTP accounts. Gmail normally requires an app
     password instead of the regular Google password.
   - **Microsoft** for Outlook, Hotmail, or Microsoft 365. Follow the device-code
     instructions. If Microsoft sign-in is not ready yet, an admin must first
     configure the Microsoft application ID.
4. Under **Server settings**, you can check or change the account label, user name,
   and the IMAP and SMTP servers.
5. Mailbox verifies the sign-in when you save. It then synchronizes every folder
   and every year. The first synchronization can take a long time for large
   accounts.

## Folder list on the left

- **All inboxes** combines the inboxes of all configured accounts.
- An account's folders are **collapsed** the first time you open Mailbox. Click
  the account name or arrow to expand or collapse them.
- Mailbox remembers this state in the current browser. Newly added accounts also
  start collapsed.
- The round dot shows the account state. The circular arrow checks the account
  immediately.
- The **gear** opens the account settings (sender, signature, sharing with
  agents, remove account).
- **Drafts** contains your saved drafts.
- **Archive only** shows mail that is no longer present on the server.

## Set the sender name and signature

1. Click the **gear** next to the account on the left.
2. Enter the name recipients should see under **Sender name**.
3. Add a **Signature** if needed, then click **Save**.

The sender address is the mail address of the configured account. You choose the
sending account while composing. The address cannot be freely replaced; sender
name and signature are configured separately for each account.

The same dialog can remove an account. This removes only access to the server:
mail that has already been archived remains in the local archive and search.

## Read and search mail

- Select a message in the middle list to open it on the right.
- External images are initially blocked for privacy. Use **Load images** if you
  want to display them for that message.
- Attachments can be downloaded below the message.
- Search covers all archived mail. Sender, recipient, and subject accept both
  `from:`/`von:`, `to:`/`an:`, and `subject:`/`betreff:`. The remaining filter
  names currently use `hat:anhang`, `vor:`, `nach:`, `konto:`, and `ordner:`.
- You can select several messages and apply bulk actions.

## Compose, reply, and drafts

- **New mail** opens the composer.
- Choose the account that sends the message in the **From** field.
- Mailbox supports **Reply**, **Reply all**, **Forward**, Cc/Bcc, and attachments.
- Drafts are saved and can be reopened from **Drafts** on the left.
- A sending limit applies per account. Once reached, Mailbox reports the limit and
  does not send additional messages.

## Deleting and the archive

**Delete** normally moves a message to the mail server's trash first. Deleting it
again from the trash removes it permanently from the server. In both cases, the
local archived copy remains and then appears under **Archive only**. The mail
archive is therefore not the same as the trash folder.

## Notifications and keyboard shortcuts

The bell enables browser notifications for new mail. Your browser asks for
permission once.

- `j` / `k`: next or previous message
- `r`: reply
- `a`: reply all
- `f`: forward
- `e`: archive
- `#`: delete
- `/`: focus search
- `c`: compose new mail

## Agents and Mailbox

Agents only see a mail account **if you share it**. Without sharing, the Mailbox
tools find nothing.

### Share an account with a project

1. Click the **gear** next to the account on the left.
2. Under **Sharing with agents**, choose a project (or **My Buddy (no project)**)
   and click **Share**.
3. From now on, agents in that project may **read** the account: search, read
   mail, and save attachments to their workspace (`mailbox-anhaenge/`).

The trash icon removes the sharing again. Removing the account also removes its
sharing.

### Who may do what?

- Only the account owner can share, and only with projects they are a member of.
- An agent sees the account only while working for a **member** of that project.
  Other projects do not see it.
- **My Buddy** applies only to your own Buddy without a project.
- Agents currently **cannot send, delete, move, or flag** mail. Drafts and sending
  with confirmation will follow in later versions.

### The tools

| Tool | Purpose |
|---|---|
| `mailbox_accounts` | shared accounts and their folders |
| `mailbox_search` | search with the same filters as the search field (at most 50 hits) |
| `mailbox_read` | read a message as text, with its attachment list |
| `mailbox_attachment` | save an attachment to the workspace (up to 25 MB, never overwrites) |

Mail text is **untrusted content**: the agent receives it explicitly marked as
such and must never follow instructions contained in it. Agents never see
credentials or passwords.

Every access is recorded in a **log** (who, when, which tool, result – without
mail content). The most recent entries are shown in the account dialog under
**Recent agent access**.

The general `read_mail` and `send_mail` tools still use the global mail
configuration and are unrelated to these accounts.

## Common problems

- **The account stays empty:** The first synchronization may still be running.
  Check the progress below the account name or click the circular arrow.
- **Sign-in rejected:** Check the user name, app password, and server settings.
  Microsoft accounts can renew their sign-in from the account dialog.
- **Sent mail is missing from the folder:** Sending can succeed even when a
  provider files the Sent copy with a delay. The local archived copy remains.
- **Folders collapse again after reloading:** The browser must not block local
  storage or clear it when closing.
