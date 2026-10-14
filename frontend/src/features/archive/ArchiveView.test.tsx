import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), put: vi.fn(), post: vi.fn() } }))
import { ArchiveView, type ArchiveViewProps } from "./ArchiveView"
import type { ArchiveEntry, ArchiveStatus } from "./api"

const STATUS: ArchiveStatus = {
  target: "local",
  storage: {
    path: "/var/lib/hydrahive2/workspaces/archive", exists: true, writable: true, count: 2, manual_count: 1,
    by_kind: { agents: 1, projects: 1 }, used_bytes: 2048, free_bytes: 14 * 1024 ** 4, trash_bytes: 512,
    is_default: true, mount: "/var/lib/hydrahive2/workspaces", setup_error: "",
  },
  share: { name: "HydraHive_Archiv", wanted: true, enabled: true, samba_installed: true, samba_running: true, login: "hh", password: "geheim-123" },
}
const ENTRIES: ArchiveEntry[] = [
  { manual: false, path: "agents/2026-10-13_101500_Alter-Agent_0450556d.tar.gz", file: "2026-10-13_101500_Alter-Agent_0450556d.tar.gz",
    kind: "agents", name: "Alter Agent", owner: "till", reason: "agent_deleted", created_at: "2026-10-13T10:15:00Z", size: 1024, mtime: 2 },
  { manual: true, path: "uploads/alte-platte.zip", file: "alte-platte.zip", kind: "uploads", size: 1024, mtime: 1 },
]
const noop = () => {}
const props = (p: Partial<ArchiveViewProps> = {}): ArchiveViewProps => ({
  status: STATUS, entries: ENTRIES, host: "192.168.178.2", kind: null, error: null,
  onKind: noop, onEmptyTrash: noop, onSetupSamba: noop, onShareSwitch: noop, onChangeLocation: noop, shareBusy: false, ...p,
})
const html = (p: Partial<ArchiveViewProps> = {}) => renderToStaticMarkup(<ArchiveView {...props(p)} />).replace(/&quot;/g, '"')

describe("Admin-Fenster Archiv & Sicherung", () => {
  it("fünf Bereiche: Speicherort, Samba-Freigabe, Laufende Vorgänge, Waisen, Elemente", () => {
    const out = html()
    const order = [...out.matchAll(/data-archive-section="([a-z]+)"/g)].map((m) => m[1])
    expect(order).toEqual(["storage", "share", "jobs", "orphans", "entries"])
    const remote = { host: "nas", share: "b", subdir: "", user: "", configured: true, password_set: false, tested: false,
      active: false, waiting: 0, last_error: null, next_try_in_s: null, on_server: 0, local_only: 2 }
    const noop = () => {}
    const withRemote = html({ status: { ...STATUS, remote }, remote: { form: { host: "nas", share: "b", subdir: "", user: "",
      password: "" }, testResult: null, busy: false, error: null, onForm: noop, onSave: noop, onTest: noop, onActive: noop, onSync: noop } })
    expect([...withRemote.matchAll(/data-archive-section="([a-z]+)"/g)].map((m) => m[1]))
      .toEqual(["storage", "share", "remote", "jobs", "orphans", "entries"])
  })

  it("Laufende Vorgänge: laufend mit Fortschritt, wartend, zuletzt mit Fehler", () => {
    const job = { kind: "project" as const, target: "p", mode: "archive" as const, error: null, bytes_total: 100,
      bytes_done: 50, files_total: 2, packages: [], leftovers: [] }
    const jobs = {
      running: { ...job, id: "r1", name: "Läuft", state: "running" as const, step: "pack" as const },
      queued: [{ ...job, id: "q1", name: "Wartet", state: "queued" as const, step: "queued" as const }],
      done: [{ ...job, id: "d1", name: "Kaputt", state: "failed" as const, step: "pack" as const, error: "pack_failed" }],
    }
    const out = html({ status: { ...STATUS, jobs } })
    expect(out).toMatch(/data-delete-job="r1" data-delete-state="running"/)
    expect(out).toContain("50%")
    expect(out).toMatch(/data-delete-job="q1" data-delete-state="queued"/)
    expect(out).toContain("delete.error.pack_failed")
    expect(html()).toContain("jobs.empty")
  })

  it("Speicherort zeigt Pfad, Zahl und Papierkorb", () => {
    const out = html()
    expect(out).toContain("/var/lib/hydrahive2/workspaces/archive")
    expect(out).toContain('data-archive-count="2"')
    expect(out).toContain("512 B")
    expect(out).toContain('data-entry-remote="local"')
  })

  it("Freigabe zeigt Netzadresse, Login und verdecktes Passwort", () => {
    const out = html()
    expect(out).toContain("\\\\192.168.178.2\\HydraHive_Archiv")
    expect(out).toContain(">hh<")
    expect(out).not.toContain("geheim-123")
  })

  it("ohne Samba: Hinweis und Knopf zum Einrichten statt Login", () => {
    const out = html({ status: { ...STATUS, share: { ...STATUS.share, enabled: false, samba_installed: false, password: "" } } })
    expect(out).toContain("share.no_samba")
    expect(out).toContain('data-archive-action="setup-samba"')
    expect(out).not.toContain(">hh<")
  })

  it("Speicherort nennt Platte und ob es der Standard bei den Projektdaten ist", () => {
    const out = html()
    expect(out).toContain('data-archive-mount="/var/lib/hydrahive2/workspaces"')
    expect(out).toContain("storage.default_hint")
    expect(html({ status: { ...STATUS, storage: { ...STATUS.storage, is_default: false } } })).not.toContain("storage.default_hint")
  })

  it("Einrichtung fehlgeschlagen: Grund wird angezeigt", () => {
    const out = html({ status: { ...STATUS, storage: { ...STATUS.storage, exists: false, setup_error: "Permission denied" } } })
    expect(out).toContain("storage.setup_failed")
    expect(out).toContain("Permission denied")
  })

  it("Freigabe-Schalter: an, aus, während des Schaltens gesperrt", () => {
    // AdminToggle = Checkbox; renderToStaticMarkup schreibt checked="" nur, wenn an.
    const sw = (out: string) => out.match(/<input[^>]*data-archive-action="share-switch"[^>]*>/)?.[0] ?? ""
    expect(sw(html())).toMatch(/\schecked=""/)
    const off = html({ status: { ...STATUS, share: { ...STATUS.share, wanted: false, enabled: false } } })
    expect(sw(off)).not.toBe("")
    expect(sw(off)).not.toMatch(/\schecked=""/)
    expect(off).toContain("share.switched_off")
    expect(off).not.toContain(">hh<")
    expect(sw(html({ shareBusy: true }))).toMatch(/\sdisabled=""/)
    // Ausgeschaltet, aber die Datei liegt noch (z. B. kurz vor dem Neuladen): kein Login anzeigen.
    const stale = html({ status: { ...STATUS, share: { ...STATUS.share, wanted: false, enabled: true } } })
    expect(stale).not.toContain(">hh<")
    expect(stale).not.toContain("HydraHive_Archiv")
  })

  it("ohne Samba kein Schalter", () => {
    const out = html({ status: { ...STATUS, share: { ...STATUS.share, enabled: false, samba_installed: false, password: "" } } })
    expect(out).not.toContain('data-archive-action="share-switch"')
  })

  it("Ort wechseln: Knopf da, während eines Umzugs gesperrt, Fortschritt sichtbar", () => {
    const b = (out: string) => out.match(/<button[^>]*data-archive-action="change-location"[^>]*>/)?.[0] ?? ""
    expect(b(html())).not.toBe("")
    expect(b(html())).not.toMatch(/\sdisabled=""/)
    const moving = html({ status: { ...STATUS, move: { running: { state: "copying", copied_bytes: 1, total_bytes: 4, target: "/x" }, last: null } } })
    expect(b(moving)).toMatch(/\sdisabled=""/)
    expect(moving).toContain('data-archive-move-percent="25"')
  })

  it("nirgends Terminal-Anweisungen (Till, 13.10.: alles über die Admin-Konsole)", () => {
    for (const s of [STATUS, { ...STATUS, share: { ...STATUS.share, enabled: false } }]) {
      const out = html({ status: s })
      expect(out).not.toMatch(/update\.sh|install\.conf|HH_ARCHIVE|sudo|Terminal/i)
    }
  })

  it("Elemente: Name, Art, Grund; Handablage markiert", () => {
    const out = html()
    expect(out).toContain("Alter Agent")
    expect(out).toContain("reason.agent_deleted")
    expect(out).toContain('data-archive-manual="uploads/alte-platte.zip"')
  })

  it("leeres Archiv: Hinweis statt Tabelle", () => {
    const out = html({ entries: [] })
    expect(out).toContain("entries.empty")
    expect(out).not.toContain("<table")
  })

  it("Papierkorb leeren nur anbietbar, wenn etwas drin ist", () => {
    // Echtes Attribut disabled="" – nicht die CSS-Klasse „disabled:…“.
    const trashButton = (out: string) => out.match(/<button[^>]*data-archive-action="empty-trash"[^>]*>/)?.[0] ?? ""
    expect(trashButton(html())).not.toMatch(/\sdisabled=""/)
    const empty = html({ status: { ...STATUS, storage: { ...STATUS.storage, trash_bytes: 0 } } })
    expect(trashButton(empty)).toMatch(/\sdisabled=""/)
  })
})
