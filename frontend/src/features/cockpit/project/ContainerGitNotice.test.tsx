import type { ReactNode } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { ProjectGitSummary } from "./ProjectGitSummary"
import { ProjectGitTreePanel } from "./ProjectGitTreePanel"

const render = (component: ReactNode) => renderToStaticMarkup(component)

describe("Container-Projekt: Git-Hinweis", () => {
  it("ersetzt den Server-Git-Status durch einen verständlichen Hinweis", () => {
    const html = render(<ProjectGitSummary projectId="p1" executionMode="container" />)

    expect(html).toContain("Git läuft im Container")
    expect(html).toContain("keine Git-Befehle auf dem Server")
    expect(html).not.toContain("Lokales Gitea")
    expect(html).not.toContain(">Pull<")
  })

  it("ersetzt auch den Git Tree und seine Server-Aktion", () => {
    const html = render(<ProjectGitTreePanel projectId="p1" executionMode="container" />)

    expect(html).toContain("Container-Repository")
    expect(html).toContain("Git läuft im Container")
    expect(html).not.toContain(">Branch<")
  })
})
