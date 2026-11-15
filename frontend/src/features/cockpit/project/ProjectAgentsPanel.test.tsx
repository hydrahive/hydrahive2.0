// Plan docs/plans/projekt-cockpit-kompakt.md: Team-Liste kompakt im Projekt-Cockpit.
import { renderToStaticMarkup } from "react-dom/server"
import { afterEach, describe, expect, it, vi } from "vitest"
import type { AgentBrief } from "@/features/chat/types"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/features/archive/delete/DeleteDialog", () => ({ DeleteDialog: () => null }))

const auth = vi.hoisted(() => ({ role: null as string | null }))
vi.mock("@/features/auth/useAuthStore", () => ({
  useAuthStore: <T,>(selector: (state: typeof auth) => T) => selector(auth),
}))

// Node hat kein Web-Storage: eigener Speicher, damit ProjectAgentDisabledGroup (liest/schreibt
// den Aufklapp-Zustand) nicht crasht.
const localStore = vi.hoisted(() => {
  const m = new Map<string, string>()
  return {
    getItem: (k: string) => (m.has(k) ? m.get(k)! : null),
    setItem: (k: string, v: string) => { m.set(k, String(v)) },
    removeItem: (k: string) => { m.delete(k) },
    clear: () => m.clear(),
  }
})
Object.defineProperty(globalThis, "localStorage", { configurable: true, value: localStore })

import { ProjectAgentsPanel } from "./ProjectAgentsPanel"

const a = (id: string, status = "active") => ({ id, name: `Agent ${id}`, llm_model: "modell-x", status }) as AgentBrief
const viele = Array.from({ length: 10 }, (_, i) => a(`s${i + 1}`))
const PROJECT_ID = "p1"
const html = (agents: AgentBrief[], selected = "lead", extra: Partial<Parameters<typeof ProjectAgentsPanel>[0]> = {}) => renderToStaticMarkup(
  <ProjectAgentsPanel agents={[a("lead"), ...agents]} projectId={PROJECT_ID} projectAgentId="lead" specialistAgentIds={agents.map((x) => x.id)}
    selectedAgentId={selected} onSelect={() => {}} {...extra} />,
).replace(/&quot;/g, '"')
const zeilen = (out: string) => [...out.matchAll(/data-team-agent="([^"]+)"/g)].map((m) => m[1])

afterEach(() => { auth.role = null; localStore.clear() })

describe("Projekt-Team kompakt (nur aktive Spezialisten + Lead)", () => {
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

describe("deaktivierte Spezialisten: eigene Gruppe statt Ausblenden oder Anhängen ans Limit", () => {
  it("stehen NICHT in der normalen (durch LIMIT begrenzten) Liste", () => {
    const out = html([a("x"), a("y", "disabled")])
    expect(zeilen(out)).not.toContain("y")
  })

  it("Gruppen-Knopf nennt die Anzahl, standardmäßig eingeklappt (kein Extra-Klick erzwungen, aber auch kein Agent verborgen ohne Hinweis)", () => {
    const out = html([a("x"), a("y", "disabled"), a("z", "disabled")])
    expect(out).toContain("team.disabled_group:{\"count\":2}")
    expect(out).toContain('data-team-disabled-group="true"')
    expect(out).toContain('aria-expanded="false"')
  })

  it("nach einmaligem Aufklappen (Zustand in localStorage je Projekt) sind alle deaktivierten ohne weiteren Klick erreichbar — auch bei 10 Stück (DEV-Projekt-Fall)", () => {
    localStore.setItem(`hh2.cockpit.disabled_team_open.${PROJECT_ID}`, "1")
    const aktive = Array.from({ length: 6 }, (_, i) => a(`a${i + 1}`))
    const deaktivierte = Array.from({ length: 10 }, (_, i) => a(`d${i + 1}`, "disabled"))
    const out = html([...aktive, ...deaktivierte])
    expect(out).toContain('aria-expanded="true"')
    for (let i = 1; i <= 10; i++) expect(zeilen(out)).toContain(`d${i}`)
    // Der "Alle anzeigen"-Knopf bezieht sich nur auf die aktiven (Lead + 6 aktive = 7), die
    // 10 deaktivierten zählen nicht mit — sie hängen nicht hinter diesem Klick.
    expect(out).toContain("Alle 7 anzeigen (3 mehr)")
  })

  it("der Aufklapp-Zustand ist je Projekt getrennt (anderes Projekt bleibt eingeklappt)", () => {
    localStore.setItem(`hh2.cockpit.disabled_team_open.other-project`, "1")
    const out = html([a("y", "disabled")])
    expect(out).toContain('aria-expanded="false"')
  })

  it("sind nicht auswählbar (disabled-Attribut am Auswahl-Button) und haben keinen „Neue Sitzung“-Knopf", () => {
    localStore.setItem(`hh2.cockpit.disabled_team_open.${PROJECT_ID}`, "1")
    const out = html([a("y", "disabled")], "lead", { onNewSession: () => {} })
    expect(out).toMatch(/data-team-agent="y"[^]*?<button[^>]*disabled[^]*?Agent y/)
    expect(out).not.toContain(`Neue Session mit Agent y`)
  })

  it("stehen mit Hinweis „deaktiviert“, wenn die Gruppe offen ist", () => {
    localStore.setItem(`hh2.cockpit.disabled_team_open.${PROJECT_ID}`, "1")
    const out = html([a("y", "disabled")])
    expect(out).toContain("team.disabled_badge")
    expect(out).toContain('data-team-agent-disabled="true"')
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

  it("auch für deaktivierte Spezialisten sichtbar, sobald die Gruppe offen ist — genau die will man wegräumen", () => {
    auth.role = "admin"
    localStore.setItem(`hh2.cockpit.disabled_team_open.${PROJECT_ID}`, "1")
    const out = html([a("x", "disabled")], "lead", { onDeleted: () => {} })
    expect(out.match(/<svg[^>]*class="lucide lucide-trash/g)?.length).toBe(1)
  })
})
