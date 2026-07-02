/** Deterministischer GrapesJS-Export → HydraHive-Template-HTML.
 *
 *  GrapesJS lagert inline `style="…"` beim Import in generiertes CSS aus —
 *  je nach Kontext als KLASSE (`.c483 { … }`) ODER als ID-Selektor
 *  (`#iqhv { … }`, abrufbar über editor.getCss()). Unser Template-Format will
 *  die Styles aber wieder inline am Element. Diese Funktion faltet BEIDE
 *  Varianten zurück in `style=""` und entfernt die von GrapesJS erzeugten
 *  id/class-Reste — dadurch entspricht der Export exakt dem handgeschriebenen
 *  Vorlagen-Format: <hh-…/>-Bausteine + Tailwind-Klassen + inline styles.
 *
 *  Verifiziert im Editor-Roundtrip (generated/gjs-editor-verify.html) mit dem
 *  echten registerHhBlocks: hh-Tags + Attribute + Gradient bleiben erhalten,
 *  keine generierten id/cNN-Reste.
 */

interface GeneratedRules {
  byClass: Record<string, string>
  byId: Record<string, string>
}

/** Extrahiert `.cNNN{…}`- UND `#id{…}`-Regeln aus dem GrapesJS-CSS. */
export function parseGeneratedRules(css: string): GeneratedRules {
  const byClass: Record<string, string> = {}
  const byId: Record<string, string> = {}
  // Klassen: .cNNN { … }  (nur GrapesJS-generierte cNNN, nicht Tailwind)
  css.replace(/\.(c\d+)\s*\{([^}]*)\}/g, (_m, cls: string, decl: string) => {
    byClass[cls] = decl.trim().replace(/\s+/g, " ")
    return ""
  })
  // ID-Selektoren: #id { … }
  css.replace(/#([\w-]+)\s*\{([^}]*)\}/g, (_m, id: string, decl: string) => {
    byId[id] = decl.trim().replace(/\s+/g, " ")
    return ""
  })
  return { byClass, byId }
}

function appendStyle(el: Element, extra: string): void {
  if (!extra) return
  const existing = el.getAttribute("style") || ""
  const sep = existing && !existing.trim().endsWith(";") ? ";" : ""
  el.setAttribute("style", (existing + sep + extra).replace(/;;+/g, ";"))
}

/** Merged GrapesJS-HTML + generiertes CSS zu inline-style-HTML.
 *
 *  @param html  Ausgabe von editor.getHtml()
 *  @param css   Ausgabe von editor.getCss()
 *  @param parse Document-Factory (Tests reichen ihr eigenes DOM rein)
 */
export function mergeInlineStyles(
  html: string,
  css: string,
  parse: (h: string) => Document = (h) => new DOMParser().parseFromString(h, "text/html"),
): string {
  const { byClass, byId } = parseGeneratedRules(css)
  const doc = parse(html)

  // 1) Klassen-basierte Regeln (.cNNN) zurück inline, cNNN aus class entfernen.
  doc.querySelectorAll("[class]").forEach((el) => {
    const keep: string[] = []
    let extra = ""
    for (const c of (el.getAttribute("class") || "").split(/\s+/).filter(Boolean)) {
      if (byClass[c]) extra += (extra && !extra.endsWith(";") ? ";" : "") + byClass[c]
      else keep.push(c)
    }
    appendStyle(el, extra)
    if (keep.length) el.setAttribute("class", keep.join(" "))
    else el.removeAttribute("class")
  })

  // 2) ID-basierte Regeln (#id) zurück inline. GrapesJS-IDs sind Zufalls-
  //    Kürzel → immer entfernen (nicht Teil unseres Template-Formats).
  doc.querySelectorAll("[id]").forEach((el) => {
    const id = el.getAttribute("id") || ""
    if (byId[id]) appendStyle(el, byId[id])
    el.removeAttribute("id")
  })

  return doc.body.innerHTML
}
