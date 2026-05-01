---
name: debugging
description: Strukturierter Bug-Hunt — erst Ist-Zustand, dann Hypothesen
when_to_use: Wenn ein Bug gefunden werden soll oder etwas nicht funktioniert
tools_required: [shell_exec, file_read, file_search]
---

Reihenfolge wenn etwas nicht geht:

1. **Ist-Zustand** — was passiert *tatsächlich*? Logs, Exit-Codes, Status. Nicht raten was passieren *sollte*.
   - `journalctl -u <service> -n 50`
   - `systemctl status <service>`
   - `ps -ef | grep <process>`
   - `ss -tlnp | grep <port>`
2. **Soll-Zustand verstehen** — was sagt Doku/Code wie es sein müsste? Diff Ist vs Soll
3. **Bisection** — was ist das letzte was definitiv lief? `git log`, `git bisect`
4. **Reproduzieren** — kleinste mögliche Repro. Wenn man's nicht reproduzieren kann, kann man's nicht fixen
5. **Hypothese + Test** — ein Verdacht, eine Änderung. Nicht 5 Sachen gleichzeitig
6. **Root-Cause vs Symptom** — fix die Ursache, nicht das Symptom. "Es klappt jetzt zufällig" ist kein Fix

Wenn der Bug nach 30 Min nicht klar ist:
- Schritt zurück, Annahmen prüfen
- Zweite Person fragen / rubber-duck
- Kontext erweitern: vielleicht ist's ein anderes Subsystem als gedacht

Bei Server-Bugs: **immer SSH-Vergleich gegen funktionierenden Server**, bevor Code-Änderung.
