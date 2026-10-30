// Plan docs/plans/admin-cockpit-kompakt.md: echter Zustand statt Erklärtext auf der Admin-Startseite.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import type { HealthCheck } from "@/features/system/api"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn() } }))
import { AdminHealthView } from "./AdminHealthPanel"

const html = (checks: HealthCheck[] | null) =>
  renderToStaticMarkup(<AdminHealthView checks={checks} onOpenSystem={() => {}} onOpenAgent={() => {}} />)

describe("Admin-Startseite: Zustand", () => {
  it("noch nicht geladen: Ladehinweis, kein Schild", () => {
    const out = html(null)
    expect(out).toContain("health.loading")
    expect(out).not.toContain("data-box-status")
  })
  it("alles ok: Schild „Läuft“, jede Prüfung als Zeile", () => {
    const out = html([{ name: "Datenbank", ok: true }, { name: "Platte", ok: true }])
    expect(out).toContain('data-box-status="ok"')
    expect(out.match(/data-check=/g)).toHaveLength(2)
  })
  it("ein Problem: Schild „Fehler“, Problem steht oben und ist markiert", () => {
    const out = html([{ name: "Datenbank", ok: true }, { name: "Neustart nötig", ok: false }])
    expect(out).toContain('data-box-status="fehler"')
    expect([...out.matchAll(/data-check="([^"]+)" data-ok="(true|false)"/g)].map((m) => `${m[1]}:${m[2]}`))
      .toEqual(["Neustart nötig:false", "Datenbank:true"])
  })
  it("Übersetzte Namen über name_code", () => {
    expect(html([{ name_code: "system_updates", ok: false }])).toContain('data-check="checks.system_updates"')
  })
  it("Knopf zum Admin-Agent bleibt", () => {
    expect(html([])).toContain("health.agent")
  })
})
