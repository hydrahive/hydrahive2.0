/** Deterministischer GrapesJS-Export → HydraHive-Template-HTML.
 *
 *  GrapesJS zieht beim Import inline `style="…"` in generierte CSS-Klassen
 *  (`.c483 { … }`, abrufbar über editor.getCss()). Unser Template-Format will
 *  die Styles aber wieder inline am Element haben. Diese Funktion faltet die
 *  generierten Klassen zurück in `style=""` — dadurch entspricht der Export
 *  exakt dem handgeschriebenen Vorlagen-Format:
 *    <hh-…/>-Bausteine + Tailwind-Klassen + inline styles.
 *
 *  Verifiziert im Proof (generated/gjs-proof.html): buddy.html import→export
 *  bleibt strukturgleich, hh-Tags + Attribute + Gradients erhalten.
 */

/** Extrahiert `.cNNN { decl }`-Regeln aus dem GrapesJS-CSS in eine Map. */
export function parseGeneratedRules(css: string): Record<string, string> {
  const map: Record<string, string> = {}
  css.replace(/\.(c\d+)\s*\{([^}]*)\}/g, (_m, cls: string, decl: string) => {
    map[cls] = decl.trim().replace(/\s+/g, " ")
    return ""
  })
  return map
}

/** Merged GrapesJS-HTML + generierte CSS-Klassen zu inline-style-HTML.
 *
 *  @param html  Ausgabe von editor.getHtml()
 *  @param css   Ausgabe von editor.getCss()
 *  @param doc   Document-Factory (Tests reichen ihr eigenes DOM rein)
 */
export function mergeInlineStyles(
  html: string,
  css: string,
  parse: (h: string) => Document = (h) => new DOMParser().parseFromString(h, "text/html"),
): string {
  const rules = parseGeneratedRules(css)
  const doc = parse(html)
  doc.querySelectorAll("[class]").forEach((el) => {
    const keep: string[] = []
    let extra = ""
    for (const c of (el.getAttribute("class") || "").split(/\s+/).filter(Boolean)) {
      if (rules[c]) extra += (extra && !extra.endsWith(";") ? ";" : "") + rules[c]
      else keep.push(c)
    }
    if (extra) {
      const existing = el.getAttribute("style") || ""
      const sep = existing && !existing.trim().endsWith(";") ? ";" : ""
      el.setAttribute("style", (existing + sep + extra).replace(/;;+/g, ";"))
    }
    if (keep.length) el.setAttribute("class", keep.join(" "))
    else el.removeAttribute("class")
  })
  return doc.body.innerHTML
}
