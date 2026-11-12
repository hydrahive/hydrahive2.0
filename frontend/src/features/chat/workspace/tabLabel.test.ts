// Reiter, die ein Modul über workspaceTabs beisteuert, hatten nur eine feste Beschriftung („Tasks“).
// Mit labelKey folgt die Beschriftung der Sprache der Oberfläche; label bleibt der Rückfall.
import { createInstance, type TFunction } from "i18next"
import { describe, expect, it } from "vitest"
import { tabLabel } from "./tabLabel"

const DICT: Record<string, string> = { "tasks:title": "Aufgaben", "leer:title": "" }
// Nachbau von i18next: Schlüssel gefunden → Text, sonst defaultValue, sonst der Schlüssel selbst.
const t = ((key: string, opts?: { defaultValue?: string }) => DICT[key] ?? opts?.defaultValue ?? key) as unknown as TFunction

describe("tabLabel", () => {
  it("ohne labelKey bleibt die feste Beschriftung", () => {
    expect(tabLabel(t, { label: "Tasks" })).toBe("Tasks")
  })

  it("mit labelKey kommt die Übersetzung", () => {
    expect(tabLabel(t, { label: "Tasks", labelKey: "tasks:title" })).toBe("Aufgaben")
  })

  it("unbekannter Schlüssel fällt auf die feste Beschriftung zurück, nicht auf den rohen Schlüssel", () => {
    expect(tabLabel(t, { label: "Tasks", labelKey: "gibtesnicht:title" })).toBe("Tasks")
  })

  it("leere Übersetzung fällt auf die feste Beschriftung zurück", () => {
    expect(tabLabel(t, { label: "Tasks", labelKey: "leer:title" })).toBe("Tasks")
  })

  it("ein labelKey, der kein Text ist, wird übergangen (Module sind nicht typgeprüft)", () => {
    expect(tabLabel(t, { label: "Tasks", labelKey: 7 as unknown as string })).toBe("Tasks")
    expect(tabLabel(t, { label: "Tasks", labelKey: "" })).toBe("Tasks")
  })
})

describe("tabLabel mit echtem i18next", () => {
  async function fixedT(lng: "de" | "en"): Promise<TFunction> {
    const instance = createInstance()
    await instance.init({
      lng, fallbackLng: "de", defaultNS: "common", ns: ["common", "workspace", "tasks"],
      interpolation: { escapeValue: false },
      resources: {
        de: { common: {}, workspace: { tab_files: "Files" }, tasks: { title: "Aufgaben" } },
        en: { common: {}, workspace: { tab_files: "Files" }, tasks: { title: "Tasks" } },
      },
    })
    // So bekommt WorkspacePanel sein t: fest auf den Namensraum workspace.
    return instance.getFixedT(lng, "workspace")
  }

  it("löst einen Schlüssel aus dem Namensraum des Moduls auf, je nach Sprache", async () => {
    expect(tabLabel(await fixedT("de"), { label: "Reiter", labelKey: "tasks:title" })).toBe("Aufgaben")
    expect(tabLabel(await fixedT("en"), { label: "Reiter", labelKey: "tasks:title" })).toBe("Tasks")
  })

  it("fällt bei unbekanntem Namensraum oder Schlüssel auf die feste Beschriftung zurück", async () => {
    const real = await fixedT("en")
    expect(tabLabel(real, { label: "Reiter", labelKey: "fehlt:title" })).toBe("Reiter")
    expect(tabLabel(real, { label: "Reiter", labelKey: "tasks:fehlt" })).toBe("Reiter")
  })
})
