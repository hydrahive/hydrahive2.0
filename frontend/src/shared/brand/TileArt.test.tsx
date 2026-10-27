// Task 0dda5420, Stufe 2: Bildchen in der Kachel – 48 px, Deko, mit Symbol als Rückfall.
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { Server } from "lucide-react"
import { TileIcon } from "./TileIcon"

describe("TileIcon", () => {
  it("mit Bildchen: 48-px-Bild als Deko, lazy, kein Symbol", () => {
    const html = renderToStaticMarkup(<TileIcon target="/vms" icon={Server} />)
    expect(html).toContain('src="/kacheln/vms.webp"')
    expect(html).toMatch(/<img[^>]*alt=""/)
    expect(html).toContain('loading="lazy"')
    expect(html).toMatch(/h-12 w-12/)
    expect(html).not.toContain("<svg")
  })
  it("ohne Bildchen: das bisherige Symbol", () => {
    const html = renderToStaticMarkup(<TileIcon target="/neu" icon={Server} />)
    expect(html).not.toContain("<img")
    expect(html).toContain("<svg")
  })
})
