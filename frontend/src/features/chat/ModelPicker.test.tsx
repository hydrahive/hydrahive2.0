import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
vi.mock("@/features/llm/api", () => ({ llmModelsApi: { byModality: () => new Promise(() => {}) } }))
import { ModelPicker } from "./ModelPicker"

describe("ModelPicker mit fester Auswahl (Option B, 14.11.2026)", () => {
  it("zeigt nur die erlaubten Modelle der Kette (nach dem ersten Effekt)", () => {
    // Server-Render: Effekt läuft nicht – das aktuelle Modell erscheint, fremde Modelle nicht.
    const html = renderToStaticMarkup(<ModelPicker current="claude-opus-5-5" onPick={() => {}}
      allowed={["claude-opus-5-5", "openai-codex/gpt-5.6-terra"]} />)
    expect(html).toContain('value="claude-opus-5-5"')
    expect(html).not.toContain("claude-fable-5")
  })
})
