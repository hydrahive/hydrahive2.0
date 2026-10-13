import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
import { ArchiveView, type ArchiveViewProps } from "./ArchiveView"
import type { ArchiveEntry, ArchiveStatus } from "./api"

const STATUS: ArchiveStatus = {
  target: "local",
  storage: {
    path: "/var/lib/hydrahive2.hdd/archive", exists: true, writable: true, count: 2, manual_count: 1,
    by_kind: { agents: 1, projects: 1 }, used_bytes: 2048, free_bytes: 14 * 1024 ** 4, trash_bytes: 512,
  },
  share: { name: "HydraHive_Archiv", enabled: true, samba_installed: true, samba_running: true, login: "hh", password: "geheim-123" },
}
const ENTRIES: ArchiveEntry[] = [
  { manual: false, path: "agents/2026-10-13_101500_Alter-Agent_0450556d.tar.gz", file: "2026-10-13_101500_Alter-Agent_0450556d.tar.gz",
    kind: "agents", name: "Alter Agent", owner: "till", reason: "agent_deleted", created_at: "2026-10-13T10:15:00Z", size: 1024, mtime: 2 },
  { manual: true, path: "uploads/alte-platte.zip", file: "alte-platte.zip", kind: "uploads", size: 1024, mtime: 1 },
]
const noop = () => {}
const props = (p: Partial<ArchiveViewProps> = {}): ArchiveViewProps => ({
  status: STATUS, entries: ENTRIES, host: "192.168.178.2", kind: null, error: null,
  onKind: noop, onEmptyTrash: noop, onSetupSamba: noop, ...p,
})
const html = (p: Partial<ArchiveViewProps> = {}) => renderToStaticMarkup(<ArchiveView {...props(p)} />).replace(/&quot;/g, '"')

describe("Admin-Fenster Archiv & Sicherung", () => {
  it("drei Bereiche: Speicherort, Samba-Freigabe, Elemente", () => {
    const out = html()
    const order = [...out.matchAll(/data-archive-section="([a-z]+)"/g)].map((m) => m[1])
    expect(order).toEqual(["storage", "share", "entries"])
  })

  it("Speicherort zeigt Pfad, Zahl und Papierkorb", () => {
    const out = html()
    expect(out).toContain("/var/lib/hydrahive2.hdd/archive")
    expect(out).toContain('data-archive-count="2"')
    expect(out).toContain("512 B")
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

  it("Samba da, Freigabe noch nicht angelegt: Hinweis auf Update", () => {
    const out = html({ status: { ...STATUS, share: { ...STATUS.share, enabled: false } } })
    expect(out).toContain("share.not_enabled")
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
