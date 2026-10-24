import { describe, expect, it, vi } from "vitest"

// Task 08c5c546: Theme-Bausteine – Modul-Bausteine erst beim Aufruf lesen.
// Die Kern-Seiten brauchen ein Browserfenster; hier reichen Platzhalter.
const mods = vi.hoisted(() => ({ value: {} as Record<string, unknown> }))
vi.mock("@/modules/index.generated", () => ({
  get moduleSlotBlocks() { return mods.value.moduleSlotBlocks },
}))
vi.mock("@/features/buddy/BuddyPage", () => ({ BuddyPage: () => null }))
vi.mock("@/features/chat/ChatPage", () => ({ ChatPage: () => null }))
vi.mock("@/features/butler/ButlerPage", () => ({ ButlerPage: () => null }))
vi.mock("@/features/teamchat/TeamchatPage", () => ({ TeamchatPage: () => null }))
vi.mock("@/features/communication/CommunicationPage", () => ({ CommunicationPage: () => null }))
vi.mock("@/features/memory/MemoryPage", () => ({ MemoryPage: () => null }))
vi.mock("@/features/skills/SkillsPage", () => ({ SkillsPage: () => null }))
vi.mock("@/features/vms/VMsPage", () => ({ VMsPage: () => null }))
vi.mock("@/features/datamining/DataminingPage", () => ({ DataminingPage: () => null }))
vi.mock("@/features/dashboard/DashboardPage", () => ({ DashboardPage: () => null }))
vi.mock("@/features/containers/ContainersPage", () => ({ ContainersPage: () => null }))
vi.mock("@/features/federation/FederationPage", () => ({ FederationPage: () => null }))
vi.mock("@/features/streaming/StreamingPage", () => ({ StreamingPage: () => null }))
vi.mock("@/features/mcp/McpPage", () => ({ McpPage: () => null }))
vi.mock("@/features/zahnfee/ZahnfeePage", () => ({ ZahnfeePage: () => null }))
vi.mock("@/features/system/TailscaleCard", () => ({ TailscaleCard: () => null }))
vi.mock("@/features/system/AgentLinkCard", () => ({ AgentLinkCard: () => null }))
vi.mock("@/features/system/MinimaxUsageCard", () => ({ MinimaxUsageCard: () => null }))
vi.mock("@/features/themetemplates/blocks/MenuBlock", () => ({ MenuBlock: () => null }))
vi.mock("@/features/themetemplates/blocks/PageBlock", () => ({ PageBlock: () => null }))

import { getBlock, slotBlocks } from "./registry"

describe("slotBlocks", () => {
  it("Modul-Bausteine kommen beim Aufruf, Kern-Bausteine bleiben", () => {
    const block = { name: "atelier", label: "Atelier", render: () => null }
    mods.value = { moduleSlotBlocks: [block] }
    expect(slotBlocks().at(-1)).toBe(block)
    expect(getBlock("Atelier")).toBe(block)
    const core = slotBlocks().length - 1
    mods.value = {}
    expect(slotBlocks()).toHaveLength(core)
    expect(core).toBeGreaterThan(0)
    expect(getBlock("werkstatt")?.label).toBe("Werkstatt (Chat)")
    expect(getBlock("atelier")).toBeUndefined()
  })
})
