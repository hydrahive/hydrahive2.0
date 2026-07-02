/** GrapesJS-Setup für den Theme-Editor: Bausteine registrieren + Export.
 *
 *  Kapselt die im Proof (PR #257) verifizierte Logik:
 *   - jeder <hh-…/> wird ein Custom Component Type → Import/Export erhält Tag
 *     UND Attribute (statt gerendert/zerstört zu werden)
 *   - Palette-Block je Baustein (Drag-Quelle)
 *   - sichtbarer Canvas-Platzhalter (man sieht den Baustein beim Bauen)
 *   - Export via mergeInlineStyles → exakt unser Vorlagen-Format
 */
import type { Editor } from "grapesjs"
import { HH_BLOCKS, defaultAttrString, type HhBlockDef } from "./blocks"
import { mergeInlineStyles } from "./exportTemplate"

/** Registriert alle hh-Bausteine als Component-Types + Palette-Blöcke. */
export function registerHhBlocks(editor: Editor): void {
  for (const def of HH_BLOCKS) {
    registerType(editor, def)
    editor.BlockManager.add(def.tag, {
      label: def.label,
      content: `<${def.tag}${defaultAttrString(def)}/>`,
      category: def.category,
      media: '<svg viewBox="0 0 24 24" width="22" height="22"><rect x="3" y="3" width="18" height="18" rx="4" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
    })
  }
}

function registerType(editor: Editor, def: HhBlockDef): void {
  editor.DomComponents.addType(def.tag, {
    isComponent: (el: HTMLElement) =>
      !!el.tagName && el.tagName.toLowerCase() === def.tag,
    model: {
      defaults: {
        tagName: def.tag,
        draggable: true,
        droppable: false,
        // Attribute → editierbare Traits im rechten Panel:
        traits: def.attrs.map((a) => ({ type: "text", name: a.name, label: a.name })),
      },
      // Export: eigener Tag mit Attributen, self-closing, kein Inhalt.
      toHTML(this: { getAttributes: () => Record<string, string> }) {
        const attrs = this.getAttributes()
        const parts = Object.entries(attrs)
          .filter(([k, v]) => v !== "" && v != null && k !== "id")
          .map(([k, v]) => `${k}="${v}"`)
        return `<${def.tag}${parts.length ? " " + parts.join(" ") : ""}/>`
      },
    },
    view: {
      onRender(this: { el: HTMLElement }) {
        this.el.style.cssText =
          "display:block;padding:16px;margin:6px 0;border:2px dashed #2dd4bf;" +
          "border-radius:12px;background:rgba(45,212,191,.10);color:#5eead4;" +
          "font:600 13px system-ui;text-align:center"
        this.el.textContent = `▣ ${def.label}  (${def.tag})`
      },
    },
  })
}

/** Exportiert den Editor-Inhalt als HydraHive-Template-HTML. */
export function exportTemplateHtml(editor: Editor): string {
  return mergeInlineStyles(editor.getHtml(), editor.getCss() || "")
}
