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
  // Till 27.10.: Köpfe waren meist nicht ganz zu sehen → Kreis 46 px, Bild 42 px, 5 px von oben:
  // gemessen liegt dann bei allen fünf Köpfen das ganze Fell mit 1,5 px Abstand im Kreis (vorher bis zu 30 % außerhalb).
  it("Kreis 46 px, Kopf passt ganz hinein", () => {
    expect(html).toMatch(/h-\[46px\] w-\[46px\]/)
    expect(html).toMatch(/top-\[5px\] h-\[42px\]/)
  })
})
