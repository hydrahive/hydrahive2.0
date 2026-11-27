import { describe, expect, it } from "vitest"
import { pinnable } from "./_pinnable"
import type { Agent } from "./types"

const tools = [
  { name: "file_read", description: "", category: "files" },
  { name: "file_write", description: "", category: "files" },
  { name: "web_search", description: "", category: "web" },
  { name: "send_mail", description: "", category: "mail" },
]

describe("pinnable – nur Freigegebenes anheftbar (Review #788)", () => {
  it("bietet eigene Tools und Tools aus eigenen Kategorien an, sonst nichts", () => {
    const draft = { tools: ["web_search", "kategorie:files"], pinned_tools: [] } as unknown as Agent
    expect(pinnable(draft, tools).map((t) => t.name).sort()).toEqual(["file_read", "file_write", "web_search"])
  })
  it("schon angeheftete bleiben sichtbar, damit man sie entfernen kann", () => {
    const draft = { tools: [], pinned_tools: ["send_mail"] } as unknown as Agent
    expect(pinnable(draft, tools).map((t) => t.name)).toEqual(["send_mail"])
  })
})
