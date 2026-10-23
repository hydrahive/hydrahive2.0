// Hilfe-Assistent (docs/plans/help-assistant.md): Darstellung des Knopfs und des Fensters.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/features/chat/Markdown", () => ({ Markdown: ({ text }: { text: string }) => <div>{text}</div> }))
import { HelpAssistantView, type HelpAssistantViewProps } from "./HelpAssistantView"

const noop = () => {}
const props = (p: Partial<HelpAssistantViewProps> = {}): HelpAssistantViewProps => ({
  open: true, status: "ready", bubbles: [], sending: false, draft: "",
  onToggle: noop, onDraft: noop, onSend: noop, onOpenLlm: noop, ...p,
})

describe("Hilfe-Assistent", () => {
  it("geschlossen: nur der runde Knopf, kein Fenster", () => {
    const html = renderToStaticMarkup(<HelpAssistantView {...props({ open: false })} />)
    expect(html).toContain('data-help-toggle="1"')
    expect(html).not.toContain('data-help-panel="1"')
  })

  it("offen: Fenster mit Eingabefeld und Begrüßung, solange kein Verlauf da ist", () => {
    const html = renderToStaticMarkup(<HelpAssistantView {...props()} />)
    expect(html).toContain('data-help-panel="1"')
    expect(html).toContain("helpdesk.welcome")
    expect(html).toContain("<textarea")
  })

  it("ohne KI-Modell: Hinweis + Knopf zu den KI-Einstellungen, kein Eingabefeld", () => {
    const html = renderToStaticMarkup(<HelpAssistantView {...props({ status: "model_missing" })} />)
    expect(html).toContain("helpdesk.model_missing")
    expect(html).toContain('data-help-open-llm="1"')
    expect(html).not.toContain("<textarea")
  })

  it("zeigt Verlauf, „sucht im Handbuch“ und Fehler", () => {
    const html = renderToStaticMarkup(<HelpAssistantView {...props({ bubbles: [
      { id: "1", role: "user", text: "Wie geht das?" },
      { id: "2", role: "assistant", text: "So geht das." },
      { id: "live", role: "assistant", text: "", busy: "search" },
    ] })} />)
    expect(html).toContain("Wie geht das?")
    expect(html).toContain("So geht das.")
    expect(html).toContain("helpdesk.busy.search")
    expect(html).not.toContain("helpdesk.welcome")
    const err = renderToStaticMarkup(<HelpAssistantView {...props({ bubbles: [{ id: "e", role: "error", text: "kaputt" }] })} />)
    expect(err).toContain('data-help-error="1"')
  })

  it("Senden gesperrt, solange eine Antwort läuft oder das Feld leer ist", () => {
    const sendBtn = (html: string) => html.match(/<button[^>]*data-help-send="1"[^>]*>/)?.[0] ?? ""
    const off = (html: string) => / disabled=""/.test(sendBtn(html))
    expect(off(renderToStaticMarkup(<HelpAssistantView {...props({ draft: "" })} />))).toBe(true)
    expect(off(renderToStaticMarkup(<HelpAssistantView {...props({ draft: "  " })} />))).toBe(true)
    expect(off(renderToStaticMarkup(<HelpAssistantView {...props({ draft: "x", sending: true })} />))).toBe(true)
    expect(off(renderToStaticMarkup(<HelpAssistantView {...props({ draft: "x" })} />))).toBe(false)
  })

  it("Fenster ist ein Dialog mit Titel (Bedienbarkeit)", () => {
    const html = renderToStaticMarkup(<HelpAssistantView {...props()} />)
    expect(html).toMatch(/role="dialog"[^>]*aria-label="helpdesk.title"/)
  })
})
