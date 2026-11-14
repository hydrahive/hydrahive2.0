// Projekt anlegen: Warnungen und Fehler zu Template-Modellen mit Link und Anleitung (Mac-User, 14.11.2026).
import { describe, expect, it } from "vitest"
import de from "@/i18n/locales/de/projects.json"
import en from "@/i18n/locales/en/projects.json"
import deErr from "@/i18n/locales/de/errors.json"
import enErr from "@/i18n/locales/en/errors.json"
import { createWarningKey, isTemplateLink, templateHint } from "./createWarnings"

const LINK = "/admin?section=llm&tab=templates&template=projekt-master"

describe("Warnungen beim Projekt-Anlegen", () => {
  it("Code → Textschlüssel; Unbekanntes fällt auf eine allgemeine Warnung", () => {
    expect(createWarningKey("template_fallback_unavailable")).toBe("create_warning.template_fallback_unavailable")
    expect(createWarningKey("template_not_configured")).toBe("create_warning.template_not_configured")
    expect(createWarningKey("irgendwas")).toBe("create_warning.general")
  })

  it("nur eigene Links auf die Template-Seite werden als Link gezeigt", () => {
    expect(isTemplateLink(LINK)).toBe(true)
    expect(isTemplateLink("/admin?section=llm&tab=templates")).toBe(true)
    for (const bad of ["https://evil.example/admin?section=llm", "//evil.example/x", "javascript:alert(1)",
      "/admin?section=users", "", undefined]) expect(isTemplateLink(bad), String(bad)).toBe(false)
  })

  it("Hinweis aus einem Fehler des Servers: Template, Modell, Link (nur bei passendem Code)", () => {
    const err = Object.assign(new Error("x"), { code: "template_primary_unavailable",
      params: { template: "projekt-master", model: "openai-codex/gpt-5.6-terra", link: LINK } })
    expect(templateHint(err)).toEqual({ template: "projekt-master", model: "openai-codex/gpt-5.6-terra", link: LINK })
    expect(templateHint(Object.assign(new Error("x"), { code: "validation_error" }))).toBeNull()
    expect(templateHint(Object.assign(new Error("x"), { code: "project_agent_invalid",
      params: { template: "projekt-master", model: "m", link: LINK } }))).toBeNull()
    expect(templateHint(Object.assign(new Error("x"), { code: "template_primary_unavailable",
      params: { template: "a", model: "b", link: "https://evil.example" } }))).toBeNull()
    expect(templateHint("kaputt")).toBeNull()
  })

  it("Texte de/en: jede Warnung, Anleitung und beide Fehler vorhanden, mit Platzhaltern", () => {
    for (const [lang, t, e] of [["de", de, deErr], ["en", en, enErr]] as const) {
      const w = (t as unknown as Record<string, Record<string, string>>).create_warning
      for (const k of ["title", "template_fallback_unavailable", "template_not_configured", "general", "how_to",
        "open_templates"]) expect(w?.[k], `${lang}:${k}`).toBeTruthy()
      expect(w.template_fallback_unavailable, lang).toContain("{{model}}")
      expect(w.template_fallback_unavailable, lang).toContain("{{template}}")
      const errs = e as Record<string, string>
      expect(errs.template_primary_unavailable, lang).toContain("{{model}}")
      expect(errs.template_primary_unavailable, lang).toContain("{{template}}")
      expect(errs.project_agent_invalid, lang).toContain("{{message}}")
    }
  })

  it("Anleitung ohne Terminal-Anweisungen (der Nutzer klickt sich durch)", () => {
    for (const t of [de, en]) {
      const all = JSON.stringify((t as Record<string, unknown>).create_warning)
      expect(all).not.toMatch(/sudo|terminal|shell|\.sh\b|HH_[A-Z_]+/i)
    }
  })
})
