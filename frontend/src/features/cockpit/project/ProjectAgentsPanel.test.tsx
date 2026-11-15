// Plan docs/plans/projekt-cockpit-kompakt.md: Team-Liste kompakt im Projekt-Cockpit.
import { renderToStaticMarkup } from "react-dom/server"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { AgentBrief } from "@/features/chat/types"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/features/archive/delete/DeleteDialog", () => ({ DeleteDialog: () => null }))

const auth = vi.hoisted(() => ({ role: null as string | null }))
vi.mock("@/features/auth/useAuthStore", () => ({
  useAuthStore: <T,>(selector: (state: typeof auth) => T) => selector(auth),
}))

import { ProjectAgentsPanel } from "./ProjectAgentsPanel"

const a = (id: string, status = "active") => ({ id, name: `Agent ${id}`, llm_model: "modell-x", status }) as AgentBrief
const viele = Array.from({ length: 10 }, (_, i) => a(`s${i + 1}`))
const html = (agents: AgentBrief[], selected = "lead", extra: Partial<Parameters<typeof ProjectAgentsPanel>[0]> = {}) => renderToStaticMarkup(
  <ProjectAgentsPanel agents={[a("lead"), ...agents]} projectAgentId="lead" specialistAgentIds={agents.map((x) => x.id)}
    selectedAgentId={selected} onSelect={() => {}} {...extra} />,
)
const zeilen = (out: string) => [...out.matchAll(/data-team-agent="([^"]+)"/g)].map((m) => m[1])

afterEach(() => { auth.role = null })

describe("Projekt-Team kompakt", () => {
  it("großes Team: 4 Zeilen, Knopf „Alle … anzeigen“ mit Rest, Suche ab 8", () => {
    const out = html(viele)
    expect(zeilen(out)).toHaveLength(4)
    expect(out).toContain("Alle 11 anzeigen (7 mehr)")
    expect(out).toContain("11 Agenten durchsuchen")
  })
  it("gewählter Agent weit hinten ist trotzdem sichtbar", () => {
    expect(zeilen(html(viele, "s9"))).toContain("s9")
  })
  it("kleines Team: alle Zeilen, kein Knopf, keine Suche", () => {
    const out = html([a("x"), a("y")])
    expect(zeilen(out)).toEqual(["lead", "x", "y"])
    expect(out).not.toContain("anzeigen (")
    expect(out).not.toContain("durchsuchen")
  })
  it("Modell sichtbar nur bei Lead und gewähltem Agenten, sonst als Tooltip", () => {
    const out = html([a("x"), a("y")], "x")
    expect(out.match(/font-mono[^>]*>modell-x</g)).toHaveLength(2)
    expect(out.match(/title="modell-x"/g)).toHaveLength(3)
  })
})

describe("deaktivierte Spezialisten (Till 15.11.: nicht mehr ausblenden, sondern ans Ende + wegräumbar)", () => {
  it("stehen am Ende der Liste und bleiben sichtbar mit Hinweis „deaktiviert“", () => {
    const out = html([a("x"), a("y", "disabled")])
    expect(zeilen(out)).toEqual(["lead", "x", "y"])
    expect(out).toContain("team.disabled_badge")
    expect(out).toContain('data-team-agent-disabled="true"')
  })

  it("sind nicht auswählbar (disabled-Attribut am Auswahl-Button) und haben keinen „Neue Sitzung“-Knopf", () => {
    const out = html([a("y", "disabled")], "lead", { onNewSession: () => {} })
    // Der Button, der onSelect auslöst, ist für den deaktivierten Agenten disabled.
    expect(out).toMatch(/data-team-agent="y"[^]*?<button[^>]*disabled[^]*?Agent y/)
    // Kein SquarePen-"Neue Sitzung"-Knopf für den deaktivierten Agenten (Titel-Attribut fehlt).
    expect(out).not.toContain(`Neue Session mit Agent y`)
  })
})

describe("Papierkorb-Symbol (1–2-Klick-Löschweg)", () => {
  it("nur für Admins sichtbar, nicht für den Projekt-Agenten", () => {
    auth.role = "admin"
    const out = html([a("x")], "lead", { onDeleted: () => {} })
    // genau ein Trash2-Icon (für den Spezialisten x), keines für lead
    expect(out.match(/<svg[^>]*class="lucide lucide-trash/g)?.length).toBe(1)
  })

  it("nicht sichtbar ohne Admin-Rolle", () => {
    auth.role = "user"
    const out = html([a("x")], "lead", { onDeleted: () => {} })
    expect(out).not.toMatch(/lucide-trash/)
  })

  it("auch für deaktivierte Spezialisten sichtbar — genau die will man wegräumen", () => {
    auth.role = "admin"
    const out = html([a("x", "disabled")], "lead", { onDeleted: () => {} })
    expect(out.match(/<svg[^>]*class="lucide lucide-trash/g)?.length).toBe(1)
  })
})
