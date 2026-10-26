import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import de from "@/i18n/locales/de/system.json"
import en from "@/i18n/locales/en/system.json"

// Echte deutsche Texte aus system.json, Platzhalter wie i18next ersetzen.
vi.mock("react-i18next", async () => {
  const d = (await import("@/i18n/locales/de/system.json")).default as { checks: Record<string, string> }
  return {
    useTranslation: () => ({
      t: (k: string, o?: Record<string, unknown>) => {
        const raw = d.checks[k.replace(/^checks\./, "")] ?? k
        return raw.replace(/\{\{(\w+)\}\}/g, (_, n: string) => String(o?.[n] ?? ""))
      },
    }),
  }
})
import { HealthBar } from "./HealthBar"

// docs/specs/system-updates.md: offene Systemupdates und „Neustart nötig“ in der Admin-Konsole.
describe("HealthBar – Systemupdates", () => {
  it("zeigt offene Updates verständlich", () => {
    const html = renderToStaticMarkup(
      <HealthBar checks={[{ name_code: "system_updates", ok: false, detail_code: "sysupd_pending", params: { count: 25 } }]} />)
    expect(html).toContain(">System<")
    expect(html).toContain("25 Updates offen – kommen mit dem nächsten Update")
  })
  it("zeigt offene Updates und Neustart zusammen", () => {
    const html = renderToStaticMarkup(
      <HealthBar checks={[{ name_code: "system_updates", ok: false, detail_code: "sysupd_pending_reboot", params: { count: 3 } }]} />)
    expect(html).toContain("3 Updates offen · Neustart des Rechners nötig")
  })
  it("Texte in beiden Sprachen, ohne Terminal-Hinweise", () => {
    const keys = ["system_updates", "sysupd_ok", "sysupd_pending", "sysupd_reboot", "sysupd_pending_reboot", "sysupd_unknown"]
    for (const k of keys) {
      const d = (de.checks as Record<string, string>)[k]
      const e = (en.checks as Record<string, string>)[k]
      expect(d, `de ${k}`).toBeTruthy()
      expect(e, `en ${k}`).toBeTruthy()
      for (const t of [d, e]) expect(t).not.toMatch(/apt|sudo|terminal|reboot-required/i)
    }
    expect((de.checks as Record<string, string>).sysupd_reboot).toBe("Neustart des Rechners nötig")
    expect((en.checks as Record<string, string>).sysupd_ok).toBe("up to date")
  })
})
