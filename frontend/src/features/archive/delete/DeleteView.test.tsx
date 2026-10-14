import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), delete: vi.fn() } }))
import { DeleteView, type DeleteViewProps } from "./DeleteView"
import { DeleteProgress } from "./DeleteProgress"
import { initialMode, type DeletePreview, type DeleteJob } from "./api"

const PREVIEW: DeletePreview = {
  kind: "project", id: "p1", name: "HDD Archive",
  agents: [{ id: "a1", name: "Projekt-Agent" }, { id: "a2", name: "Helfer" }], chats: 7,
  projects: [{ id: "p1", name: "HDD Archive" }], members: {}, mounts_skipped: ["mounts/nas"],
  hand_over: 0, memberships: 0, stays: {},
  size: { bytes: 5 * 1024 ** 3, complete: false },
  archive: { path: "/var/lib/hydrahive2/workspaces/archive", share: "HydraHive_Archiv", free_bytes: 14 * 1024 ** 4, possible: true, reason: null },
}
const noop = () => {}
const props = (p: Partial<DeleteViewProps> = {}): DeleteViewProps => ({
  preview: PREVIEW, mode: "archive", typed: "", busy: false, error: null,
  onMode: noop, onTyped: noop, onStart: noop, ...p,
})
const html = (p: Partial<DeleteViewProps> = {}) => renderToStaticMarkup(<DeleteView {...props(p)} />).replace(/&quot;/g, '"')
const start = (out: string) => out.match(/<button[^>]*data-delete-action="start"[^>]*>/)?.[0] ?? ""
const radio = (out: string, mode: string) => out.match(new RegExp(`<button[^>]*data-delete-mode="${mode}"[^>]*>`))?.[0] ?? ""

describe("Lösch-Dialog", () => {
  it("„Ins Archiv“ ist vorausgewählt, „Unwiderruflich“ nie", () => {
    expect(initialMode(PREVIEW)).toBe("archive")
    expect(initialMode({ ...PREVIEW, archive: { ...PREVIEW.archive, possible: false, reason: "not_enough_space" } })).toBeNull()
    const out = html()
    expect(radio(out, "archive")).toContain('aria-checked="true"')
    expect(radio(out, "permanent")).toContain('aria-checked="false"')
  })

  it("nennt Ziel, freien Platz, Freigabe und was betroffen ist", () => {
    const out = html()
    expect(out).toContain("/var/lib/hydrahive2/workspaces/archive")
    expect(out).toContain("HydraHive_Archiv")
    expect(out).toContain("14.0 TB")
    expect(out).toContain("Helfer")
    expect(out).toContain('"count":7')
    expect(out).toContain("mounts/nas")
    expect(out).toContain("size.at_least")
  })

  it("gesperrter Archiv-Weg zeigt den Grund und ist nicht wählbar", () => {
    const blocked = { ...PREVIEW, archive: { ...PREVIEW.archive, possible: false, reason: "not_enough_space" } }
    const out = html({ preview: blocked, mode: null })
    expect(radio(out, "archive")).toMatch(/\sdisabled=""/)
    expect(out).toContain("reason.not_enough_space")
    expect(radio(out, "permanent")).toContain('aria-checked="false"')
    // Selbst wenn „archive“ noch gewählt ist (Platz ging während des Dialogs weg): kein Start.
    expect(start(html({ preview: blocked, mode: "archive" }))).toMatch(/\sdisabled=""/)
  })

  it("Unwiderruflich: Knopf erst nach exakt eingetipptem Namen", () => {
    expect(start(html({ mode: "permanent", typed: "" }))).toMatch(/\sdisabled=""/)
    expect(start(html({ mode: "permanent", typed: "hdd archive" }))).toMatch(/\sdisabled=""/)
    expect(start(html({ mode: "permanent", typed: "HDD Archive " }))).toMatch(/\sdisabled=""/)
    expect(start(html({ mode: "permanent", typed: "HDD Archive" }))).not.toMatch(/\sdisabled=""/)
  })

  it("Ins Archiv: Knopf ohne Namen; ohne Auswahl gesperrt", () => {
    expect(start(html({ mode: "archive" }))).not.toMatch(/\sdisabled=""/)
    expect(start(html({ mode: null }))).toMatch(/\sdisabled=""/)
    expect(start(html({ mode: "archive", busy: true }))).toMatch(/\sdisabled=""/)
    expect(html({ mode: "archive" })).not.toMatch(/<input/)
  })

  it("sagt, dass Chats verschwinden und was beim Nutzer bleibt", () => {
    const user = { ...PREVIEW, kind: "user" as const, stays: { vms: 2, containers: 1, smb_mounts: 0 }, hand_over: 3 }
    const out = html({ preview: user })
    expect(out).toContain("chats_gone")
    expect(out).toContain('stays.vms:{"count":2}')
    expect(out).toContain('hand_over:{"count":3}')
    expect(out).not.toContain("stays.smb_mounts")
  })
})

describe("Fortschritt", () => {
  const job = (p: Partial<DeleteJob>): DeleteJob => ({
    id: "j1", kind: "project", target: "p1", name: "HDD Archive", mode: "archive", state: "running", step: "pack",
    error: null, bytes_total: 1000, bytes_done: 250, files_total: 10, packages: [], leftovers: [], ...p,
  })

  it("zeigt Schritt und Anteil", () => {
    const out = renderToStaticMarkup(<DeleteProgress job={job({})} />)
    expect(out).toContain("step.pack")
    expect(out).toContain("25%")
  })

  it("Fehler nennt den Grund und dass nichts gelöscht wurde", () => {
    const out = renderToStaticMarkup(<DeleteProgress job={job({ state: "failed", error: "umount_failed" })} />)
    expect(out).toContain("error.umount_failed")
    expect(out).toContain("nothing_deleted")
  })

  it("fertig mit stehengebliebenem Laufwerk meldet es", () => {
    const out = renderToStaticMarkup(<DeleteProgress job={job({ state: "done", step: "done", leftovers: ["/x/daten/usb"], package: "a.tar.gz" })} />)
    expect(out).toContain("/x/daten/usb")
    expect(out).toContain("a.tar.gz")
  })
})
