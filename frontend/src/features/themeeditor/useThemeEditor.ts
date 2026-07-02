/** State + Aktionen für die Theme-Editor-Seite.
 *
 *  Hält das aktive Theme/die Route, lädt Template-HTML, speichert und
 *  publisht über die Editor-API (Etappe 2). Die eigentliche GrapesJS-Instanz
 *  lebt in der Komponente; dieser Hook kennt sie nur über eine Ref-Setzfunktion.
 */
import { useCallback, useEffect, useState } from "react"
import type { Editor } from "grapesjs"
import {
  listThemes,
  listTemplates,
  getTemplate,
  saveTemplate,
  forkTheme,
  publishTheme,
} from "@/features/themes/api"
import { exportTemplateHtml } from "./setupEditor"

export interface EditorTheme {
  id: string
  name: string
  protected: boolean
}

export function useThemeEditor() {
  const [themes, setThemes] = useState<EditorTheme[]>([])
  const [themeId, setThemeId] = useState<string>("")
  const [routes, setRoutes] = useState<string[]>([])
  const [route, setRoute] = useState<string>("")
  const [html, setHtml] = useState<string>("")
  const [isProtected, setIsProtected] = useState(false)
  const [status, setStatus] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [editor, setEditor] = useState<Editor | null>(null)

  // Installierte (Ordner-)Themes laden — nur die haben Templates.
  useEffect(() => {
    listThemes()
      .then((idx) => {
        const list = idx.installed
          .filter((t) => t.loaded)
          .map((t) => ({ id: t.id, name: t.name ?? t.id, protected: !!t.protected }))
        setThemes(list)
        if (list.length && !themeId) setThemeId(list[0].id)
      })
      .catch((e) => setStatus(String(e)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Bei Theme-Wechsel: Routen laden.
  useEffect(() => {
    if (!themeId) return
    listTemplates(themeId)
      .then((r) => {
        setRoutes(r.routes)
        setIsProtected(r.protected)
        setRoute(r.routes[0] ?? "")
      })
      .catch((e) => setStatus(String(e)))
  }, [themeId])

  // Bei Route-Wechsel: Template-HTML laden.
  useEffect(() => {
    if (!themeId || !route) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setHtml("")
      return
    }
    getTemplate(themeId, route)
      .then((r) => setHtml(r.html))
      .catch((e) => setStatus(String(e)))
  }, [themeId, route])

  const save = useCallback(async () => {
    if (!editor || !themeId || !route) return
    setBusy(true)
    setStatus(null)
    try {
      const out = exportTemplateHtml(editor)
      await saveTemplate(themeId, route, out)
      setStatus(`„${route}" gespeichert.`)
    } catch (e) {
      setStatus(String(e))
    }
    setBusy(false)
  }, [editor, themeId, route])

  const fork = useCallback(async (newId: string, newName: string) => {
    setBusy(true)
    setStatus(null)
    try {
      const r = await forkTheme(themeId, newId, newName)
      const nt = { id: r.id, name: r.name, protected: false }
      setThemes((prev) => [...prev, nt])
      setThemeId(r.id)
      setStatus(`Kopie „${r.name}" angelegt — jetzt editierbar.`)
    } catch (e) {
      setStatus(String(e))
    }
    setBusy(false)
  }, [themeId])

  const publish = useCallback(() => {
    if (!themeId) return
    setBusy(true)
    setStatus("Veröffentliche …")
    publishTheme(
      themeId,
      (line) => setStatus(line),
      () => { setStatus("Veröffentlicht — Neustart läuft."); setBusy(false) },
      (msg) => { setStatus(`Fehler: ${msg}`); setBusy(false) },
    )
  }, [themeId])

  return {
    themes, themeId, setThemeId,
    routes, route, setRoute,
    html, isProtected, status, busy,
    setEditor, save, fork, publish,
  }
}
