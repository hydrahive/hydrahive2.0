import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
const post = vi.fn()
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), put: vi.fn(), post: (...a: unknown[]) => post(...a) } }))
import { ArchiveEntriesSection } from "./ArchiveEntriesSection"
import { DropLocalView } from "./DropLocalDialog"
import { RemoteView, type RemoteViewProps } from "./RemoteSection"
import { archiveApi, remoteStateOf, type ArchiveEntry, type ArchiveRemote } from "./api"
import { DeleteProgress } from "./delete/DeleteProgress"
import type { DeleteJob } from "./delete/api"

const pkg = (p: Partial<ArchiveEntry>): ArchiveEntry => ({
  manual: false, path: "agents/a.tar.gz", file: "a.tar.gz", kind: "agents", name: "A", size: 2048, mtime: 1,
  local: true, ...p,
})
const ENTRIES: ArchiveEntry[] = [
  pkg({ path: "agents/oben.tar.gz", name: "Oben", remote: { state: "verified" } }),
  pkg({ path: "agents/wartet.tar.gz", name: "Wartet", remote: { state: "pending" } }),
  pkg({ path: "agents/nur-oben.tar.gz", name: "Nur oben", local: false, remote: { state: "remote_only" } }),
  { manual: true, path: "uploads/hand.pdf", file: "hand.pdf", kind: "uploads", size: 4, mtime: 1, remote: { state: "verified" } },
]
const entriesHtml = (onDrop = () => {}) => renderToStaticMarkup(
  <ArchiveEntriesSection entries={ENTRIES} kind={null} onKind={() => {}} onDropLocal={onDrop} />)
const dropButtons = (out: string) => [...out.matchAll(/data-entry-drop="([^"]+)"/g)].map((m) => m[1])

const R: ArchiveRemote = {
  host: "192.168.178.3", share: "Hydrahive_backups", subdir: "hydrahive", user: "till", configured: true,
  password_set: true, tested: true, active: true, waiting: 0, last_error: null, next_try_in_s: null,
  on_server: 9, local_only: 0, remote_only: 0, droppable: 9, droppable_bytes: 67 * 1024 ** 2,
}
const noop = () => {}
const remoteHtml = (p: Partial<RemoteViewProps> = {}) => renderToStaticMarkup(<RemoteView remote={R}
  form={{ host: R.host, share: R.share, subdir: R.subdir, user: R.user, password: "" }} testResult={null} busy={false}
  error={null} onForm={noop} onSave={noop} onTest={noop} onActive={noop} onSync={noop} onDropAll={noop} {...p} />)
  .replace(/&quot;/g, '"')
const dropAll = (out: string) => out.match(/<[a-z]+[^>]*data-remote-action="drop-all"[^>]*>/)?.[0] ?? ""

const progress = (job: DeleteJob) => renderToStaticMarkup(<DeleteProgress job={job} />).replace(/&quot;/g, '"')

const JOB: DeleteJob = {
  id: "j1", kind: "drop_local", target: "drop_local", name: "2 Pakete", mode: "drop", state: "done", step: "done",
  error: null, bytes_total: 4096, bytes_done: 4096, files_total: 2, packages: [], leftovers: [],
  done_paths: ["agents/a.tar.gz"], kept: [{ path: "agents/b.tar.gz", reason: "verify_failed" }], freed_bytes: 2048,
}

describe("Lokale Kopie löschen (Etappe 3b)", () => {
  it("Stand je Paket kennt „nur auf dem Server“", () => {
    expect(remoteStateOf({ remote: { state: "remote_only" } })).toBe("server_only")
    expect(remoteStateOf({ remote: { state: "verified" } })).toBe("server")
  })

  it("Knopf nur bei Paketen, die geprüft auf dem Server liegen – nie bei von Hand Abgelegtem", () => {
    const out = entriesHtml()
    expect(dropButtons(out)).toEqual(["agents/oben.tar.gz"])
    expect(out).toContain('data-entry-remote="server_only"')
    expect(out).toContain("entries.remote.server_only")
  })

  it("Gesamt-Knopf zeigt Anzahl und Größe, ohne lösbare Pakete gesperrt", () => {
    const out = remoteHtml()
    expect(out).toContain('remote.drop_all:{"count":9,"size":"67.0 MB"}')
    expect(dropAll(out)).not.toMatch(/\sdisabled=""/)
    expect(dropAll(remoteHtml({ remote: { ...R, droppable: 0, droppable_bytes: 0 } }))).toMatch(/\sdisabled=""/)
    expect(dropAll(remoteHtml({ busy: true }))).toMatch(/\sdisabled=""/)
    expect(remoteHtml({ remote: { ...R, active: false } })).not.toContain('data-remote-action="drop-all"')
  })

  it("Dialog nennt Ort der Server-Kopie und frei werdenden Platz, ohne Namen-Eintippen", () => {
    const out = renderToStaticMarkup(<DropLocalView remote={R} count={2} bytes={4096} busy={false} error={null}
      onConfirm={noop} onClose={noop} />).replace(/&quot;/g, '"')
    expect(out).toContain("\\\\192.168.178.3\\Hydrahive_backups\\hydrahive")
    expect(out).toContain('drop.text:{"count":2,"size":"4.0 KB"}')
    expect(out).not.toContain("<input")
    expect(out.match(/<button[^>]*data-drop-action="confirm"[^>]*>/)?.[0]).not.toMatch(/\sdisabled=""/)
  })

  it("Fortschritt: Ergebnis mit frei gewordenem Platz und behaltenen Paketen samt Grund", () => {
    const out = progress(JOB)
    expect(out).toContain('drop.done:{"count":1,"size":"2.0 KB"}')
    expect(out).toContain("agents/b.tar.gz")
    expect(out).toContain("drop.kept.verify_failed")
    expect(out).not.toContain("delete.done_archive")
    const failed = progress({ ...JOB, state: "failed", error: "unreachable", done_paths: [], kept: [] })
    expect(failed).toContain("drop.error.unreachable")
    expect(failed).toContain("delete.nothing_deleted")
    const halfway = progress({ ...JOB, state: "failed", error: "interrupted" })
    expect(halfway).not.toContain("delete.nothing_deleted")
    expect(halfway).toContain('drop.done:{"count":1,"size":"2.0 KB"}')
  })

  it("Schnittstelle: einzelne Pfade oder alle", async () => {
    post.mockResolvedValue({ job_id: "x", count: 1 })
    await archiveApi.dropLocal({ paths: ["agents/oben.tar.gz"] })
    await archiveApi.dropLocal({ all_verified: true })
    expect(post.mock.calls).toEqual([
      ["/admin/archive/entries/drop-local", { paths: ["agents/oben.tar.gz"] }],
      ["/admin/archive/entries/drop-local", { all_verified: true }],
    ])
  })
})
