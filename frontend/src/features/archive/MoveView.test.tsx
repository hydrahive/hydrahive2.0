import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
import { MoveView, type MoveViewProps } from "./MoveView"
import { MoveProgress } from "./MoveProgress"
import type { ArchiveLocation } from "./api"

const LOCS: ArchiveLocation[] = [
  { id: "default", kind: "default", path: "/var/lib/hydrahive2/workspaces/archive", mount: "", device: "", fstype: "",
    size_bytes: 0, free_bytes: 14 * 1024 ** 4, writable: true, current: true, problems: [] },
  { id: "aaaaaaaaaaaa", kind: "disk", path: "/srv/fast/hydrahive-archiv", mount: "/srv/fast", device: "/dev/md127",
    fstype: "ext4", size_bytes: 500 * 1024 ** 3, free_bytes: 400 * 1024 ** 3, writable: true, current: false, problems: [] },
  { id: "bbbbbbbbbbbb", kind: "disk", path: "/media/usb/hydrahive-archiv", mount: "/media/usb", device: "/dev/sdc1",
    fstype: "ext4", size_bytes: 1024 ** 4, free_bytes: 1024 ** 4, writable: false, current: false, problems: ["target_not_writable"] },
  { id: "cccccccccccc", kind: "disk", path: "/mnt/klein/hydrahive-archiv", mount: "/mnt/klein", device: "/dev/sdd1",
    fstype: "ext4", size_bytes: 1024 ** 2, free_bytes: 10, writable: true, current: false, problems: ["not_enough_space"] },
]
const noop = () => {}
const props = (p: Partial<MoveViewProps> = {}): MoveViewProps => ({
  locations: LOCS, selected: null, busy: false, preparing: false, error: null,
  onSelect: noop, onMove: noop, onPrepare: noop, ...p,
})
const html = (p: Partial<MoveViewProps> = {}) => renderToStaticMarkup(<MoveView {...props(p)} />).replace(/&quot;/g, '"')
const btn = (out: string, action: string) => out.match(new RegExp(`<button[^>]*data-archive-action="${action}"[^>]*>`))?.[0] ?? ""

describe("Ort wechseln", () => {
  it("listet Standard und Platten mit freiem Platz, aktueller Ort markiert", () => {
    const out = html()
    expect([...out.matchAll(/data-archive-location="([a-z0-9]+)"/g)].map((m) => m[1]))
      .toEqual(["default", "aaaaaaaaaaaa", "bbbbbbbbbbbb", "cccccccccccc"])
    expect(out).toMatch(/data-archive-location="default"[^>]*data-current="true"/)
    expect(out).toContain("/srv/fast")
    expect(out).toContain("400.0 GB")
  })

  it("kein freies Pfadfeld", () => {
    expect(html()).not.toMatch(/<input[^>]*type="text"/)
  })

  it("Umziehen erst nach Auswahl eines möglichen Ziels", () => {
    expect(btn(html(), "move-start")).toMatch(/\sdisabled=""/)
    expect(btn(html({ selected: "aaaaaaaaaaaa" }), "move-start")).not.toMatch(/\sdisabled=""/)
    expect(btn(html({ selected: "cccccccccccc" }), "move-start")).toMatch(/\sdisabled=""/)
    expect(btn(html({ selected: "aaaaaaaaaaaa", busy: true }), "move-start")).toMatch(/\sdisabled=""/)
  })

  it("Probleme werden benannt", () => {
    const out = html()
    expect(out).toContain("problem.not_enough_space")
    expect(out).toContain("problem.target_not_writable")
  })

  it("Platte ohne Schreibrecht: Knopf zum Einrichten statt Terminal-Anweisung", () => {
    const out = html({ selected: "bbbbbbbbbbbb" })
    expect(btn(out, "prepare-disk")).not.toBe("")
    expect(btn(html({ selected: "bbbbbbbbbbbb", preparing: true }), "prepare-disk")).toMatch(/\sdisabled=""/)
    expect(btn(html({ selected: "aaaaaaaaaaaa" }), "prepare-disk")).toBe("")
    expect(out).not.toMatch(/sudo|chown|chmod|Terminal/i)
  })

  it("Hinweis: vorhandene Pakete ziehen mit, Freigabe ruht währenddessen", () => {
    expect(html({ selected: "aaaaaaaaaaaa" })).toContain("move.explain")
  })
})

describe("Fortschritt des Umzugs", () => {
  it("zeigt Prozent und Bytes", () => {
    const out = renderToStaticMarkup(<MoveProgress move={{ running: { state: "copying", copied_bytes: 512, total_bytes: 1024,
      total_files: 4, target: "/srv/fast/hydrahive-archiv" }, last: null }} />).replace(/&quot;/g, '"')
    expect(out).toContain('data-archive-move-percent="50"')
    expect(out).toContain("move.state.copying")
  })

  it("Ergebnis: fertig mit übrig gebliebenen Dateien bzw. Fehler mit Grund", () => {
    const done = renderToStaticMarkup(<MoveProgress move={{ running: null, last: { state: "done", target: "/x",
      left_behind: ["uploads/spaet.txt"] } }} />)
    expect(done).toContain("move.done")
    expect(done).toContain("uploads/spaet.txt")
    const failed = renderToStaticMarkup(<MoveProgress move={{ running: null, last: { state: "failed", error: "verify_failed", detail: "" } }} />)
    expect(failed).toContain("move.error.verify_failed")
  })

  it("nichts gelaufen: nichts anzeigen", () => {
    expect(renderToStaticMarkup(<MoveProgress move={{ running: null, last: null }} />)).toBe("")
  })
})
