HydraHive lässt sich auf vier Wegen erweitern. Sie unterscheiden sich darin, **was** sie hinzufügen und **wie viel Vertrauen** sie brauchen.

| Art | Was es ist | Wo | Wer installiert |
|---|---|---|---|
| **Modul** | Eine ganze Funktion mit eigener Seite, oft mit eigenen Daten und Agenten-Werkzeugen (z. B. [[Haushaltsbuch]], [[Atelier]], [[Tickets]]) | Modul-Hub [`hydrahive2-modules`](https://github.com/hydrahive/hydrahive2-modules) | Admin unter **Einstellungen → Module** |
| **Theme** | Aussehen und Aufbau der Oberfläche | Theme-Hub | Admin unter **Einstellungen → Themes**; jeder wählt im **Profil** Design und Farbschema |
| **[[Plugin|Plugins]]** | Zusätzliche Werkzeuge für Agenten | Plugin-Hub | Admin |
| **[[Extension|Extensions]]** | Fremde Dienste auf dem Server, z. B. Gitea, Ollama, SearXNG | mitgeliefert | Admin; Installer laufen mit erhöhten Rechten |

## 🧩 Module
- Installieren, aktualisieren und entfernen mit einem Klick. Danach baut HydraHive die Oberfläche neu und startet kurz neu.
- **Beim Entfernen bleiben die Daten des Moduls erhalten.** Installierst du es wieder, ist alles noch da.
- Viele Module sind anfangs **nur für Admins** freigeschaltet. Andere Nutzer bekommen sie über [[Freigaben & Gruppen|Freigaben-und-Gruppen]].
- Sensible Module (z. B. [[Haushaltsbuch]], [[Cryptoboard]], [[Meine Akte|Meine-Akte]]) liegen hinter dem [[Vault]].

## 🎨 Themes
- **Design** (z. B. Menü oben oder links) und **Farbschema** wählt jeder im **Profil**. Die Auswahl wird im Browser gespeichert.
- Der **Theme-Editor** (Admin) baut Seiten per Ziehen und Ablegen. Mitgelieferte Themes sind geschützt; zum Ändern erst eine Kopie anlegen.
- Die großen Cockpits (Buddy, Projekte, Media, Vault, Admin) behalten ihr eigenes Aussehen.

## ⚠️ Vertrauen
**Extensions** führen Installationsskripte mit erhöhten Rechten aus. Installiere nur, was du kennst. Module und Plugins aus den offiziellen Hubs werden geprüft, laufen aber trotzdem mit den Rechten von HydraHive.

---
*Quelle: [README](https://github.com/hydrahive/hydrahive2.0/blob/main/README.de.md#module-versus-extensions).*
