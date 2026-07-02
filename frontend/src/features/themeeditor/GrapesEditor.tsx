/** GrapesJS-Canvas als React-Komponente.
 *
 *  Kapselt den GrapesJS-Lifecycle: init beim Mount, destroy beim Unmount.
 *  Nutzt GrapesJS' eingebaute Panels (Blocks links, Traits/Settings rechts),
 *  damit wir kein eigenes Palette-/Attribut-UI bauen müssen.
 *
 *  - `initialHtml`  wird beim Laden in den Canvas gesetzt
 *  - `onReady`      liefert die Editor-Instanz nach oben (für Export/Save)
 */
import { useEffect, useRef } from "react"
import grapesjs, { type Editor } from "grapesjs"
import "grapesjs/dist/css/grapes.min.css"
import { registerHhBlocks } from "./setupEditor"

interface Props {
  initialHtml: string
  onReady: (editor: Editor) => void
}

export function GrapesEditor({ initialHtml, onReady }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const editorRef = useRef<Editor | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const editor = grapesjs.init({
      container: containerRef.current,
      height: "100%",
      width: "auto",
      storageManager: false,
      // Eingebaute Panels: Blocks + Settings (Traits) einblenden.
      blockManager: { appendTo: "#hh-gjs-blocks" },
      traitManager: { appendTo: "#hh-gjs-traits" },
      panels: { defaults: [] },
      // Kein Style-Manager-Sektor nötig — wir editieren Layout/Bausteine, nicht
      // Feindesign (das kommt aus Tailwind/Theme-Variablen).
      styleManager: { sectors: [] },
    })

    registerHhBlocks(editor)
    editor.setComponents(initialHtml || "")
    editorRef.current = editor
    onReady(editor)

    return () => {
      editor.destroy()
      editorRef.current = null
    }
    // Nur einmal beim Mount initialisieren; initialHtml-Wechsel via key-Prop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex h-full min-h-0 w-full">
      <div
        id="hh-gjs-blocks"
        className="w-52 shrink-0 overflow-y-auto border-r border-white/10 bg-black/20"
      />
      <div ref={containerRef} className="min-w-0 flex-1" />
      <div
        id="hh-gjs-traits"
        className="w-60 shrink-0 overflow-y-auto border-l border-white/10 bg-black/20"
      />
    </div>
  )
}
