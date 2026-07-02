import { useCallback, useEffect, useState } from "react"
import { DEFAULT_WIDGET_ORDER } from "./widgets"

const STORAGE_KEY = "hh-dashboard-layout"

export interface DashboardLayout {
  /** Widget-IDs in Anzeige-Reihenfolge. */
  order: string[]
  /** IDs, die ausgeblendet sind. */
  hidden: string[]
}

function defaultLayout(): DashboardLayout {
  return { order: [...DEFAULT_WIDGET_ORDER], hidden: [] }
}

/** Gespeichertes Layout laden und mit den aktuell verfügbaren Widgets
 *  abgleichen: neue Widget-IDs werden ans Ende gehängt (sichtbar), entfernte
 *  IDs fallen raus. So bleibt eine gespeicherte Anordnung nach einem Update
 *  gültig, ohne neue Widgets zu verschlucken. */
function loadLayout(): DashboardLayout {
  let stored: Partial<DashboardLayout> | null = null
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) stored = JSON.parse(raw)
  } catch {
    stored = null
  }
  const known = new Set(DEFAULT_WIDGET_ORDER)
  const storedOrder = Array.isArray(stored?.order) ? stored!.order.filter((id) => known.has(id)) : []
  const missing = DEFAULT_WIDGET_ORDER.filter((id) => !storedOrder.includes(id))
  const order = [...storedOrder, ...missing]
  const hidden = Array.isArray(stored?.hidden) ? stored!.hidden.filter((id) => known.has(id)) : []
  return { order, hidden }
}

export function useDashboardLayout() {
  const [layout, setLayout] = useState<DashboardLayout>(loadLayout)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(layout))
    } catch {
      /* ignore */
    }
  }, [layout])

  const move = useCallback((id: string, dir: -1 | 1) => {
    setLayout((prev) => {
      const order = [...prev.order]
      const i = order.indexOf(id)
      const j = i + dir
      if (i < 0 || j < 0 || j >= order.length) return prev
      ;[order[i], order[j]] = [order[j], order[i]]
      return { ...prev, order }
    })
  }, [])

  const toggle = useCallback((id: string) => {
    setLayout((prev) => {
      const hidden = prev.hidden.includes(id)
        ? prev.hidden.filter((h) => h !== id)
        : [...prev.hidden, id]
      return { ...prev, hidden }
    })
  }, [])

  const reset = useCallback(() => setLayout(defaultLayout()), [])

  const isHidden = useCallback((id: string) => layout.hidden.includes(id), [layout.hidden])

  return { layout, move, toggle, reset, isHidden }
}
