import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"
import de from "@/i18n/locales/de/projects.json"
import en from "@/i18n/locales/en/projects.json"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))

import { WebhookAutoNotice } from "./WebhookAutoNotice"

describe("WebhookAutoNotice", () => {
  it("zeigt Hinweis und Bestätigungsknopf", () => {
    const html = renderToStaticMarkup(<WebhookAutoNotice busy={false} onAck={() => {}} />)
    expect(html).toContain("webhook-auto-notice")
    expect(html).toContain("webhook.auto_title")
    expect(html).toContain("webhook.auto_ack")
  })

  it("Knopf ist während der Anfrage gesperrt", () => {
    const html = renderToStaticMarkup(<WebhookAutoNotice busy onAck={() => {}} />)
    expect(html).toContain("disabled")
  })

  it("i18n-Schlüssel in de und en vorhanden und nennen den Header", () => {
    for (const w of [de.webhook, en.webhook]) {
      for (const k of ["auto_title", "auto_body", "auto_ack", "ack_failed"] as const) {
        expect(w[k].length).toBeGreaterThan(5)
      }
      expect(w.auto_body).toContain("X-Webhook-Secret")
    }
  })
})
