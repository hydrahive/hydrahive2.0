# Spec: Host-Self-Heal nach Ubuntu-26.04-Upgrade

Status: umgesetzt
Datum: 2026-08-22
Ausgelöst durch: Produktionsvorfall auf HydrahiveHome am 2026-08-21

## Problem

Nach dem Distro-Upgrade auf Ubuntu 26.04 traten auf dem Produktionsserver zwei
Host-Fehler auf, die der Installer bisher nicht kennt. Beide sind nicht
HydraHive-spezifisch, sondern Folge des Upgrades — jeder der zehn Kunden trifft
sie beim gleichen Schritt.

### P1 — `/tmp` wird zur RAM-Disk

Ubuntu 26.04 aktiviert die systemd-Vendor-Unit `tmp.mount`. Damit wird `/tmp`
als `tmpfs` gemountet und liegt im RAM (hier: 16 GB statt 14 TB Plattenplatz).

Beobachtete Folge: Beim Kopieren großer Mediendateien lief `/tmp` voll, RAM und
Swap gerieten unter Druck, SQLite-Commits blockierten. Das Backend meldete
`sqlite3.OperationalError: database is locked`, der Event-Loop stockte und
Streaming-Downloads brachen mit „Internal Error“ ab.

Der Code-Fix (PR #404) härtet den Downloader gegen die *Symptome*. Diese Spec
beseitigt die *Ursache*.

### P1 — DNS fällt systemweit aus

Zwei Effekte wirkten zusammen:

1. Das Upgrade setzte `/etc/systemd/resolved.conf` auf den Werkszustand zurück.
   Der Stub-Listener von `systemd-resolved` belegte wieder `127.0.0.53:53`.
2. Incus legt beim Start für eine verwaltete Bridge (hier `hh-voice`) einen
   eigenen `dnsmasq` an. Dieser hält TCP auf der Bridge-IP `:53` und verhindert
   damit den Wildcard-Bind (`0.0.0.0:53`) eines Host-DNS-Servers wie Pi-hole.

Ergebnis: Pi-holes internes `dnsmasq` scheiterte mit
`failed to create listening socket for port 53: Address in use` — der Host
hatte keine Namensauflösung mehr.

Besonders tückisch: `systemctl is-active pihole-FTL` meldet dabei **`active`**.
Der Ausfall entgeht jedem Healthcheck, der nur den Unit-Status prüft.

Der Anteil, für den HydraHive verantwortlich ist: `installer/modules/55-voice.sh`
legt die Bridge per `incus network create` ohne abgeschaltetes DNS an. Bei uns
blieb sie sogar als ungenutzte Leiche zurück (`used_by: []`), weil der Container
über `br0` läuft.

## Ziel

`installer/update.sh` heilt beide Zustände selbstständig, ohne Rückfrage und
idempotent. Neue Voice-Bridges entstehen von vornherein konfliktfrei.

## Nicht-Ziele

- Kein Eingriff, wenn kein Host-DNS-Server auf Port 53 vorhanden ist. Auf einem
  normalen Server ist der resolved-Stub korrekt und bleibt unangetastet.
- Kein Löschen der `hh-voice`-Bridge, auch wenn sie ungenutzt ist. Der DHCP-Teil
  bleibt funktionsfähig; nur DNS wird abgeschaltet.
- Kein Neustart von Fremddiensten außer dem gezielten `pihole-FTL`-Restart,
  wenn dessen DNS nachweislich tot ist.
- Kein automatischer Reboot. Das Aushängen eines aktiven `/tmp`-tmpfs ist
  unsicher (offene Dateihandles), deshalb wird nur maskiert und der Nutzer
  informiert.

## Entwurf

Neue gemeinsame Bibliothek `installer/lib/host-selfheal.sh`, gesourct von
`update.sh`. Analog zu `lib/python-venv.sh`: reine Funktionen, testbar ohne
root, Logging über die vorhandene `log`-Funktion.

### `hh_fix_tmp_on_tmpfs`

1. `/tmp` in `/etc/fstab` definiert? → **niemals maskieren**, Rückgabe 0. Eine
   bereits gesetzte Maskierung wird aufgehoben. Begründung im Nachtrag unten.
2. Kein `tmpfs` auf `/tmp`? → nichts tun, Rückgabe 0.
3. `tmp.mount` bereits maskiert? → nichts tun (idempotent).
4. Sonst: `systemctl mask tmp.mount` und Hinweis loggen, dass die Änderung
   erst nach dem nächsten Reboot greift.

Bewusst kein `umount`: Läuft der Dienst, sind Dateien offen — ein erzwungenes
Aushängen im laufenden Update würde Prozesse beschädigen.

### `hh_fix_resolved_stub`

1. Kein Host-DNS-Server, der Wildcard-`:53` will? → nichts tun.
   Erkennung: aktive Unit aus `pihole-FTL`, `dnsmasq`, `named`, `unbound`.
2. Stub-Listener nicht aktiv? → nichts tun.
3. Sonst: Drop-in `/etc/systemd/resolved.conf.d/10-hydrahive-no-stub.conf` mit
   `DNSStubListener=no` schreiben, `/etc/resolv.conf` von `stub-resolv.conf`
   auf `resolv.conf` umhängen, `systemd-resolved` neu starten.

Das Drop-in überlebt künftige Distro-Upgrades — anders als die vom Upgrade
überschriebene `resolved.conf` selbst.

### `hh_fix_incus_bridge_dns`

Für jede *verwaltete* Incus-Bridge:

1. `raw.dnsmasq` enthält bereits `port=0`? → nichts tun.
2. Kein konkurrierender Host-DNS-Server? → nichts tun.
3. Sonst: `incus network set <bridge> raw.dnsmasq port=0`.

DHCP bleibt aktiv — Container behalten ihre Adressen. Nur der DNS-Teil des
Bridge-`dnsmasq` verschwindet, und damit der Port-53-Konflikt.

### `hh_fix_pihole_ordering`

Ist `pihole-FTL` vorhanden und Incus installiert, wird ein Drop-in
`After=incus.service` geschrieben. Das entschärft das Boot-Rennen zusätzlich
zum abgeschalteten Bridge-DNS.

### `hh_verify_dns`

Abschließende Wirkprüfung: Ist ein Host-DNS-Server aktiv, aber die Auflösung
über `127.0.0.1` schlägt fehl, wird der Dienst einmal neu gestartet und erneut
geprüft. Bleibt es defekt, erscheint eine deutliche Warnung im Update-Log —
der Update-Lauf bricht deswegen aber nicht ab.

### `55-voice.sh`

`incus network create` erhält direkt `raw.dnsmasq=port=0`. Damit entsteht eine
neue Bridge gar nicht erst im Konfliktzustand.

## Testbarkeit

Die Funktionen kapseln alle Systemaufrufe hinter überschreibbaren Kommandos
(`systemctl`, `incus`, `dig`), sodass Tests sie über `PATH`-Stubs simulieren
können — ohne root und ohne echte Systemänderung. Das folgt dem Muster der
bestehenden Installer-Tests.

## Akzeptanzkriterien

- Jede Funktion ist bei zweiter Ausführung wirkungslos (idempotent).
- Ohne Host-DNS-Server bleibt der resolved-Stub unverändert.
- Ohne `tmpfs` auf `/tmp` bleibt `tmp.mount` unverändert.
- Steht `/tmp` in `/etc/fstab`, bleibt `tmp.mount` unmaskiert — unabhängig vom
  Dateisystemtyp des laufenden Mounts.
- DHCP der Voice-Bridge funktioniert nach dem Fix weiter.
- Ein fehlgeschlagener Teilschritt bricht das Update nicht ab.
- Das Kunden-Runbook beschreibt beide Symptome samt Verifikationsbefehlen.

## Nachtrag 2026-09-01 — Maskierung nur bei der Vendor-Unit

Ausgelöst durch: Workstation-Ausfall auf tills-master-wks am 2026-08-31

Die ursprüngliche Fassung maskierte `tmp.mount`, sobald `/tmp` ein `tmpfs` war.
Sie unterschied dabei nicht, *woher* dieses `tmpfs` stammt — und genau darin lag
ein Fehler mit Totalausfall als Folge.

Definiert `/etc/fstab` einen `/tmp`-Eintrag, erzeugt der systemd-fstab-generator
daraus selbst eine `tmp.mount` und trägt sie unter `local-fs.target.requires`
ein: eine **harte** Abhängigkeit. Eine maskierte Unit kann niemals starten,
`local-fs.target` bleibt damit dauerhaft unerfüllbar. In der Folge läuft
`systemd-remount-fs` nie, `/` wird nie von `ro` auf `rw` umgestellt und der Host
bootet nicht mehr durch.

Die Vendor-Unit aus Ubuntu 26.04 hängt dagegen nur per `WantedBy` (weich) an
`local-fs.target`. Nur sie darf maskiert werden.

Das Fehlerbild ist irreführend: Sichtbar wird eine Reihe scheinbar
zusammenhangloser Dienste, die beim Start scheitern — `swap`, incus-Sockets,
`snapd`, `smbd`, `sysstat`, `grub-common`, `nginx`, `docker`. Ihr gemeinsamer
Nenner ist lediglich, dass sie Schreibzugriff brauchen. Auch das Fehlen
jeglicher Journale der Fehlboots gehört zum Bild, denn `journald` kann auf ein
read-only `/var/log` nichts schreiben. Der Recovery-Modus funktioniert weiter,
weil `friendly-recovery` sein eigenes `mount -o remount,rw /` absetzt.

Diagnose-Abkürzung: Scheitern viele unzusammenhängende Dienste und existiert
kein Journal des Fehlboots, zuerst `mount | grep ' / '` prüfen und dann die
Target-Kette mit `systemctl is-active local-fs-pre.target local-fs.target` —
nicht Pakete, Treiber oder `fsck`.

`hh_fix_tmp_on_tmpfs` prüft die fstab jetzt vor allem anderen und nimmt eine
bereits gesetzte Maskierung zurück, damit betroffene Hosts sich selbst heilen.
Wer `/tmp` auf einem solchen Host auf die Platte holen will, entfernt die
`/tmp`-Zeile aus `/etc/fstab` und startet neu — Maskieren ist dort kein Mittel.
