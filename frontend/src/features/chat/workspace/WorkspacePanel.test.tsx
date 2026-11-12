import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

const lang = vi.hoisted(() => ({ value: "de" }))
const mods = vi.hoisted(() => ({ value: {} as Record<string, unknown> }))
vi.mock("@/modules/index.generated", () => ({ get moduleWorkspaceTabs() { return mods.value.moduleWorkspaceTabs } }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(), post: vi.fn() }, buildErrorMessage: vi.fn() }))
vi.mock("react-i18next", () => {
  const texts: Record<string, Record<string, string>> = {
    de: { "tasks:title": "Aufgaben", tab_files: "Files", tab_git: "Git" },
    en: { "tasks:title": "Tasks", tab_files: "Files", tab_git: "Git" },
  }
  const t = (key: string, opts?: { defaultValue?: string }) => texts[lang.value][key] ?? opts?.defaultValue ?? key
  return { useTranslation: () => ({ t }) }
})

import { WorkspacePanel } from "./WorkspacePanel"

function Tab() { return <div>tab-inhalt</div> }
const panel = () => renderToStaticMarkup(<WorkspacePanel agentId="a1" onOpenFile={() => {}} />)

describe("WorkspacePanel: Beschriftung der Modul-Reiter", () => {
  it("mit labelKey folgt der Reiter der Sprache", () => {
    mods.value = { moduleWorkspaceTabs: [{ id: "tasks", label: "Reiter fest", labelKey: "tasks:title", component: Tab }] }
    lang.value = "de"
    expect(panel()).toContain(">Aufgaben</button>")
    lang.value = "en"
    const html = panel()
    expect(html).toContain(">Tasks</button>")
    expect(html).not.toContain("Reiter fest")
  })

  it("ohne labelKey bleibt die feste Beschriftung des Moduls", () => {
    lang.value = "en"
    mods.value = { moduleWorkspaceTabs: [{ id: "x", label: "Reiter fest", component: Tab }] }
    expect(panel()).toContain(">Reiter fest</button>")
  })

  it("unbekannter labelKey zeigt die feste Beschriftung, nicht den rohen Schlüssel", () => {
    mods.value = { moduleWorkspaceTabs: [{ id: "x", label: "Reiter fest", labelKey: "fehlt:title", component: Tab }] }
    const html = panel()
    expect(html).toContain(">Reiter fest</button>")
    expect(html).not.toContain("fehlt:title")
  })

  it("Kern-Reiter bleiben", () => {
    mods.value = {}
    const html = panel()
    expect(html).toContain(">Files</button>")
    expect(html).toContain(">Git</button>")
  })
})
