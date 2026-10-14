import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), put: vi.fn(), post: vi.fn() } }))
import { RemoteView, type RemoteViewProps } from "./RemoteSection"
import { remoteStateOf, type ArchiveRemote } from "./api"

const R: ArchiveRemote = {
  host: "192.168.178.3", share: "Hydrahive_backups", subdir: "hydrahive", user: "till",
  configured: true, password_set: true, tested: true, active: true,
  waiting: 0, last_error: null, next_try_in_s: null, on_server: 9, local_only: 0,
  remote_only: 0, droppable: 0, droppable_bytes: 0,
}
const noop = () => {}
const props = (p: Partial<RemoteViewProps> = {}): RemoteViewProps => ({
  remote: R, form: { host: R.host, share: R.share, subdir: R.subdir, user: R.user, password: "" },
  testResult: null, busy: false, error: null,
  onForm: noop, onSave: noop, onTest: noop, onActive: noop, onSync: noop, ...p,
})
const html = (p: Partial<RemoteViewProps> = {}) => renderToStaticMarkup(<RemoteView {...props(p)} />).replace(/&quot;/g, '"')
const btn = (out: string, a: string) => out.match(new RegExp(`<[a-z]+[^>]*data-remote-action="${a}"[^>]*>`))?.[0] ?? ""

describe("Bereich Externer Server", () => {
  it("Passwort-Feld ist leer und sagt, dass eines gespeichert ist", () => {
    const out = html()
    expect(out).toContain('data-archive-section="remote"')
    const pw = out.match(/<input[^>]*name="password"[^>]*>/)?.[0] ?? ""
    expect(pw).toContain('type="password"')
    expect(pw).toMatch(/value=""/)
    expect(out).toContain("remote.password_kept")
  })

  it("aktiv schalten nur nach Test", () => {
    expect(btn(html({ remote: { ...R, tested: false, active: false } }), "active")).toMatch(/\sdisabled=""/)
    expect(btn(html(), "active")).not.toMatch(/\sdisabled=""/)
  })

  it("zeigt wartende Pakete, Grund und nächsten Versuch", () => {
    const out = html({ remote: { ...R, waiting: 3, last_error: "unreachable", next_try_in_s: 300 } })
    expect(out).toContain('data-remote-waiting="3"')
    expect(out).toContain("remote.error.unreachable")
    expect(out).toContain("remote.next_try")
  })

  it("Testergebnis: Fehler mit Grund, Erfolg mit freiem Platz", () => {
    expect(html({ testResult: { ok: false, error: "auth_failed" } })).toContain("remote.error.auth_failed")
    expect(html({ testResult: { ok: true, free_bytes: 29 * 1024 ** 4 } })).toContain('remote.test_ok:{"free":"29.0 TB"}')
  })

  it("nicht eingetragen: kein Abgleich, kein Schalter frei", () => {
    const out = html({ remote: { ...R, configured: false, tested: false, active: false, password_set: false } })
    expect(btn(out, "sync")).toMatch(/\sdisabled=""/)
    expect(btn(out, "active")).toMatch(/\sdisabled=""/)
    expect(out).not.toContain("remote.password_kept")
  })

  it("Stand je Paket", () => {
    expect(remoteStateOf({ remote: { state: "verified" } })).toBe("server")
    expect(remoteStateOf({ remote: { state: "pending" } })).toBe("waiting")
    expect(remoteStateOf({})).toBe("local")
  })
})
