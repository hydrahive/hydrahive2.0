// Hinweise beim Projekt-Anlegen als statisches Markup.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({
  t: (k: string, o?: { model?: string; template?: string }) => (o?.model ? `${k}[${o.template}|${o.model}]` : k),
}) }))
import { ProjectCreateNotices } from "./ProjectCreateNotices"

const LINK = "/admin?section=llm&tab=templates&template=projekt-master"
const W = { code: "template_fallback_unavailable", template: "projekt-master", model: "openai-codex/gpt-5.6-terra",
  link: LINK }

describe("Hinweise beim Projekt-Anlegen", () => {
  it("ohne Warnung und Hinweis: nichts", () => {
    expect(renderToStaticMarkup(<ProjectCreateNotices />)).toBe("")
  })

  it("Warnung: Titel, Text mit Template und Modell, Anleitung, Link, Weiter", () => {
    const out = renderToStaticMarkup(<ProjectCreateNotices warnings={[W]} onContinue={() => {}} />)
    for (const s of ["create_warning.title",
      "create_warning.template_fallback_unavailable[projekt-master|openai-codex/gpt-5.6-terra]", "create_warning.how_to", `href="${LINK.replace(/&/g, "&amp;")}"`, "create_warning.open_templates",
      "create_warning.continue"]) expect(out).toContain(s)
    expect(out).toContain('role="status"')
  })

  it("abgelehnt (Hauptmodell fehlt): Alarm mit Anleitung und Link, kein Weiter", () => {
    const out = renderToStaticMarkup(<ProjectCreateNotices hint={{ template: "projekt-master", model: "x", link: LINK }} />)
    expect(out).toContain('role="alert"')
    expect(out).toContain("create_warning.primary_how_to")
    expect(out).toContain("create_warning.open_templates")
    expect(out).not.toContain("create_warning.continue")
    expect(out).not.toContain("create_warning.title")
  })

  it("fremder Link aus der Antwort wird nicht gezeigt", () => {
    const out = renderToStaticMarkup(<ProjectCreateNotices warnings={[{ ...W, link: "https://evil.example" }]} />)
    expect(out).not.toContain("evil.example")
    expect(out).not.toContain("create_warning.open_templates")
  })
})
