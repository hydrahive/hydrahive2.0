"""E-Mail als eingehender Kommunikationsweg (Schicht 1).

`watcher.run_loop` pollt ein IMAP-Postfach und reicht neue Mails über
`communication.router.handle_incoming` an Butler/Master — die Antwort geht
per SMTP zurück. Eine globale Mailbox, einem HydraHive-User zugeordnet
(`settings.mail_owner_username`). Per-Buddy-Postfächer und KAS-Provisioning
sind bewusst NICHT hier.
"""
