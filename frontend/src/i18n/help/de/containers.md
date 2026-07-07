# Container

## Was ist das?

Container sind **leichtgewichtige, abgeschottete Dienste** — ähnlich wie VMs,
aber viel schlanker und schneller. Technisch sind es **Linux-Container (LXC via
incus)**: Sie teilen sich den Kernel des Hosts und starten in Sekunden, ohne den
Overhead einer kompletten virtuellen Maschine.

**Faustregel:** Willst du ein **komplettes fremdes Betriebssystem** (z.B. Windows)
→ nimm eine **VM**. Willst du einen **einzelnen Linux-Dienst** schlank laufen
lassen (z.B. eine Such-Engine, ein Passwort-Manager, ein Bookmark-Tool) → nimm
einen **Container**.

## Wozu ist das gut?

Ideal für kleine, dauerhaft laufende Dienste — Beispiele wie in der Eingabemaske
vorgeschlagen: **searxng** (Suche), **vaultwarden** (Passwörter), **linkding**
(Bookmarks). Jeder Dienst läuft isoliert, kann aber über das Netzwerk erreichbar
sein.

## Kernbegriffe

- **Image** — die Vorlage, aus der ein Container gebaut wird (z.B. ein Ubuntu- oder
  Debian-Basis-Image). Du kannst aus den **Quick-Images** wählen oder einen
  eigenen **Image-Alias** eingeben.
- **Bridged / Isoliert** — Netzwerk-Betriebsart (wie bei VMs): bridged = eigene
  IP im LAN, isoliert = kein Netzzugang.
- **CPU-/RAM-Limit** — optionale Obergrenzen. Leer = unbegrenzt (der Container
  darf sich nehmen, was da ist).

## Schritt-für-Schritt: Container erstellen

1. **Container erstellen** klicken.
2. **Name** vergeben (1–63 Zeichen, beginnt mit Buchstabe, nur `a-z A-Z 0-9 -`) —
   z.B. `searxng`.
3. **Image** wählen (aus den Quick-Images oder eigener Alias).
4. Optional **CPU-Limit** und **RAM-Limit (MB)** setzen — leer lassen = unbegrenzt.
5. **Netzwerk** wählen: **Bridged (br0)** für eine eigene LAN-IP, **Isoliert** für
   keinen Netzzugang.
6. **Container erstellen** → er startet und erscheint in der Liste.

## Die Detail-Ansicht (Tabs)

Ein Klick auf einen Container öffnet die Detail-Ansicht mit vier Reitern:

- **Config** — Einstellungen (Name, Beschreibung, CPU/RAM, Image). Das Image ist
  read-only — für ein anderes Image den Container neu erstellen.
- **Konsole** — eine Shell im Container, direkt im Browser.
- **Logs** — das Lifecycle-Log (`incus info --show-log`), hilft bei Startproblemen.
- **Stats** — Live-Auslastung (CPU/RAM) — nur wenn der Container läuft.

## Typische Fehler

- **„Image fehlt"** — Beim Anlegen wurde kein Image gewählt. Eins aus der Liste
  nehmen oder einen gültigen Alias eintippen.
- **„Name ungültig"** — 1–63 Zeichen, beginnt mit Buchstabe, nur `a-z A-Z 0-9 -`.
- **Keine Live-Stats** — Der Container läuft nicht; erst starten.
- **Kein Netzwerk im Container** — Netzwerk steht auf **Isoliert**; auf
  **Bridged** umstellen.

## Container oder VM?

| | Container (LXC/incus) | VM (QEMU/KVM) |
|---|---|---|
| Gewicht | leicht, Sekunden-Start | schwer, eigener Kernel |
| Betriebssystem | Linux (teilt Host-Kernel) | beliebig (auch Windows) |
| Wofür | einzelne Dienste | komplette Fremdsysteme |

## Tipps

- **Ein Dienst pro Container** — sauberer zu warten und neu zu starten.
- **Limits nur wenn nötig**: Für die meisten kleinen Dienste reicht „unbegrenzt";
  Limits setzt du, wenn ein Container den Host nicht überlasten soll.
- **Bridged**, wenn du den Dienst von anderen Geräten im Netz erreichen willst.
