import { useCallback, useEffect, useLayoutEffect, useRef } from "react"

/** Nächsten scrollbaren Vorfahren finden (assistant-ui Viewport). */
function getScrollParent(node: HTMLElement | null): HTMLElement | null {
  let el = node?.parentElement ?? null
  while (el) {
    const overflowY = getComputedStyle(el).overflowY
    if (overflowY === "auto" || overflowY === "scroll") return el
    el = el.parentElement
  }
  return null
}

/**
 * Lädt ältere Nachrichten nach, sobald ein Sentinel oben in den sichtbaren
 * Bereich scrollt (IntersectionObserver). Nach dem Nachladen wird die
 * Scroll-Position erhalten, damit der Thread nicht nach oben springt und der
 * Observer nicht sofort erneut feuert.
 *
 * `dep` ist die sichtbare Nachrichtenanzahl — ändert sie sich, korrigieren wir
 * die Scroll-Position um die neu oben eingefügte Höhe.
 *
 * WICHTIG (Bugfix): Der Scroll-Container wird LAZY beim Registrieren des
 * Observers gesucht, nicht einmalig beim Mount. Beim ersten Render ist die
 * Nachrichtenliste noch leer → hasMore=false → der Sentinel rendert `null` →
 * die Ref ist leer. Ein Mount-Effekt mit leerem Dep-Array hätte dann dauerhaft
 * `null` gecached, der Observer wäre nie registriert worden und der Thread
 * hätte beim Hochscrollen nie nachgeladen (sichtbar als dauerhaftes
 * „Ältere Nachrichten werden geladen …“).
 */
export function useLoadOlder(
  hasMore: boolean,
  onLoadMore: () => void,
  dep: number,
) {
  const sentinelRef = useRef<HTMLDivElement>(null)
  const scrollParentRef = useRef<HTMLElement | null>(null)
  const prevScrollHeight = useRef(0)
  const loadMoreRef = useRef(onLoadMore)
  loadMoreRef.current = onLoadMore

  /** Container bei Bedarf (neu) auflösen — Ergebnis wird gecached. */
  const resolveScrollParent = useCallback(() => {
    if (scrollParentRef.current?.isConnected) return scrollParentRef.current
    scrollParentRef.current = getScrollParent(sentinelRef.current)
    return scrollParentRef.current
  }, [])

  useEffect(() => {
    if (!hasMore) return
    const el = sentinelRef.current
    if (!el) return

    let observer: IntersectionObserver | null = null
    let raf = 0
    let attempts = 0

    // Der Viewport kann eine Runde später im DOM landen (assistant-ui rendert
    // asynchron). Deshalb ein paar Frames lang erneut versuchen, statt still
    // aufzugeben.
    const attach = () => {
      const root = resolveScrollParent()
      if (!root) {
        if (attempts++ < 30) raf = requestAnimationFrame(attach)
        return
      }
      observer = new IntersectionObserver(
        (entries) => {
          if (entries[0]?.isIntersecting) {
            prevScrollHeight.current = root.scrollHeight
            loadMoreRef.current()
          }
        },
        { root, threshold: 0 },
      )
      observer.observe(el)
    }
    attach()

    return () => {
      if (raf) cancelAnimationFrame(raf)
      observer?.disconnect()
    }
  }, [hasMore, dep, resolveScrollParent])

  useLayoutEffect(() => {
    const root = scrollParentRef.current
    if (!root || !prevScrollHeight.current) return
    const diff = root.scrollHeight - prevScrollHeight.current
    if (diff > 0) root.scrollTop += diff
    prevScrollHeight.current = 0
  }, [dep])

  return sentinelRef
}
