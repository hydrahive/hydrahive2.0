// Fehlerbericht-Karte (docs/plans/help-error-report.md): Senden nur per Klick, ohne Mailkonto mailto + Einrichten-Link.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
const { HelpReportCardView } = await import("./HelpReportCardView")
type P = Parameters<typeof HelpReportCardView>[0]

const base: P = { phase: "ready", subject: "[HydraHive-Fehler] X – /mailbox", body: "Beschreibung (Nutzer):\n<b>kaputt</b>",
  to: "issue@hydrahive.org", mailAccount: true, canSetup: false, onSend: () => {}, onDiscard: () => {}, onCopy: () => {},
  onSetupMail: () => {} }
const view = (p: Partial<P> = {}) => renderToStaticMarkup(<HelpReportCardView {...base} {...p} />)

describe("Fehlerbericht-Karte", () => {
  it("mit Mailkonto: voller Text als Text (kein HTML), Senden + Verwerfen, Empfänger sichtbar", () => {
    const h = view()
    expect(h).toContain('data-help-report-send="1"')
    expect(h).toContain('data-help-report-discard="1"')
    expect(h).toContain("&lt;b&gt;kaputt&lt;/b&gt;")
    expect(h).not.toContain("<b>kaputt")
    expect(h).toContain("report.to")
    expect(h).not.toContain("data-help-report-mailto")
  })

  it("ohne Mailkonto: kein Senden-Knopf, mailto-Link + Kopieren", () => {
    const h = view({ mailAccount: false, mailto: "mailto:issue@hydrahive.org?subject=x&body=y" })
    expect(h).not.toContain('data-help-report-send="1"')
    expect(h).toContain('data-help-report-mailto="1"')
    expect(h).toContain('href="mailto:issue@hydrahive.org?subject=x&amp;body=y"')
    expect(h).toContain("report.copy")
  })

  it("Einrichten-Link nur für Admins, sonst Hinweis", () => {
    expect(view({ mailAccount: false, canSetup: true })).toContain('data-help-report-setup="1"')
    const user = view({ mailAccount: false, canSetup: false })
    expect(user).not.toContain("data-help-report-setup")
    expect(user).toContain("report.ask_admin")
  })

  it("gekürzt-Hinweis, Fehlermeldung, Senden gesperrt während des Sendens", () => {
    expect(view({ mailAccount: false, mailto: "mailto:x", truncated: true })).toContain("report.truncated")
    expect(view({ error: "Verbindung abgelehnt" })).toContain('role="alert"')
    expect(view({ phase: "sending" })).toMatch(/data-help-report-send="1"[^>]*disabled|disabled=""[^>]*data-help-report-send/)
  })

  it("Endzustände ohne Knöpfe", () => {
    for (const phase of ["sent", "gone", "discarded"] as const) {
      const h = view({ phase })
      expect(h).toContain(`data-help-report="${phase}"`)
      expect(h).not.toContain("data-help-report-send")
    }
  })
})
