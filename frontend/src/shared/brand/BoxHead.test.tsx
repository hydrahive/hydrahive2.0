// Plan docs/plans/hydra-box-koepfe.md, Task 2: kleiner Hydra-Kopf im Box-Kopf.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { BoxHead } from "./BoxHead"
import { BOX_THEMES } from "./boxThemes"

describe("BoxHead", () => {
  const html = renderToStaticMarkup(<BoxHead theme="werkzeug" />)
  it("zeigt den Kopf des Themas als Deko", () => {
    expect(html).toContain(`src="${BOX_THEMES.werkzeug.head}"`)
    expect(html).toContain('alt=""')
    expect(html).toContain('aria-hidden="true"')
    expect(html).toContain('loading="lazy"')
  })
  it("Name des Kopfes als Hinweis beim Überfahren", () => {
    expect(html).toContain('title="Macher"')
  })
  it("feste Größe 36 px", () => {
    expect(html).toMatch(/h-9 w-9/)
  })
})
