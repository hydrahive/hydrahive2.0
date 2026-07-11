import { useEffect, useLayoutEffect, useRef } from "react"

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

  useEffect(() => {
    scrollParentRef.current = getScrollParent(sentinelRef.current)
  }, [])

  useEffect(() => {
    if (!hasMore) return
    const el = sentinelRef.current
    const root = scrollParentRef.current
    if (!el || !root) return
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          prevScrollHeight.current = root.scrollHeight
          loadMoreRef.current()
        }
      },
      { root, threshold: 0 },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [hasMore, dep])

  useLayoutEffect(() => {
    const root = scrollParentRef.current
    if (!root || !prevScrollHeight.current) return
    const diff = root.scrollHeight - prevScrollHeight.current
    if (diff > 0) root.scrollTop += diff
    prevScrollHeight.current = 0
  }, [dep])

  return sentinelRef
}
