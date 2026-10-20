import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { useDialog } from "./useDialog"

// docs/specs/ui-standard.md, Regel 6: ein Aufruf liefert alle Dialog-Attribute,
// und die Überschrift ist über aria-labelledby verknüpft.
function Probe() {
  const dlg = useDialog()
  return <div {...dlg.props} className="fixed inset-0"><h2 id={dlg.titelId}>Titel</h2></div>
}

describe("useDialog", () => {
  const html = renderToStaticMarkup(<Probe />)

  it("setzt role=dialog, aria-modal und tabIndex=-1", () => {
    expect(html).toContain('role="dialog"')
    expect(html).toContain('aria-modal="true"')
    expect(html).toContain('tabindex="-1"')
  })

  it("aria-labelledby zeigt auf die id der Überschrift", () => {
    const labelledby = html.match(/aria-labelledby="([^"]+)"/)?.[1]
    const titelId = html.match(/<h2 id="([^"]+)"/)?.[1]
    expect(labelledby).toBeTruthy()
    expect(labelledby).toBe(titelId)
  })
})
