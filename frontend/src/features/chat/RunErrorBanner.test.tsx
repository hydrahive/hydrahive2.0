import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { RunErrorBanner } from "./RunErrorBanner"

const noop = () => {}

describe("RunErrorBanner", () => {
  it("rendert nichts ohne Fehler", () => {
    expect(renderToStaticMarkup(<RunErrorBanner error={null} errorKind={null} continueLabel="Weiter" onContinue={noop} />)).toBe("")
  })

  it("zeigt den Fehlertext als Alert", () => {
    const html = renderToStaticMarkup(
      <RunErrorBanner error="Das Modell hat die Antwort abgelehnt" errorKind="refusal" continueLabel="Weiter" onContinue={noop} />,
    )
    expect(html).toContain("Das Modell hat die Antwort abgelehnt")
    expect(html).toContain('role="alert"')
    expect(html).not.toContain("Weiter")
  })

  it("zeigt den Weitermachen-Button nur bei max_iterations", () => {
    const html = renderToStaticMarkup(
      <RunErrorBanner error="Max erreicht" errorKind="max_iterations" continueLabel="Weitermachen" onContinue={noop} />,
    )
    expect(html).toContain("Weitermachen")
  })
})
