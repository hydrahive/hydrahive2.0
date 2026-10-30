// Plan docs/plans/projekt-cockpit-kompakt.md: Team-Liste kompakt im Projekt-Cockpit.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import type { AgentBrief } from "@/features/chat/types"
import { ProjectAgentsPanel } from "./ProjectAgentsPanel"

const a = (id: string) => ({ id, name: `Agent ${id}`, llm_model: "modell-x" }) as AgentBrief
const viele = Array.from({ length: 10 }, (_, i) => a(`s${i + 1}`))
const html = (agents: AgentBrief[], selected = "lead") => renderToStaticMarkup(
  <ProjectAgentsPanel agents={[a("lead"), ...agents]} projectAgentId="lead" specialistAgentIds={agents.map((x) => x.id)}
    selectedAgentId={selected} onSelect={() => {}} />,
)
const zeilen = (out: string) => [...out.matchAll(/data-team-agent="([^"]+)"/g)].map((m) => m[1])

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
