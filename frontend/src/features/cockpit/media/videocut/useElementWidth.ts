import { useEffect, useRef, useState } from "react"

/** Misst die Breite eines Elements live (ResizeObserver). Für die dynamische
 *  Timeline-Skalierung, damit die Spuren die volle verfügbare Breite füllen. */
export function useElementWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const update = () => setWidth(el.clientWidth)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  return { ref, width }
}
