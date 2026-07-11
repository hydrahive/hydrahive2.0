import { Loader2 } from "lucide-react"
import { useLoadOlder } from "./_useLoadOlder"

interface Props {
  hasMore: boolean
  onLoadMore: () => void
  /** Sichtbare Nachrichtenanzahl — treibt Scroll-Korrektur nach dem Nachladen. */
  visibleCount: number
}

/**
 * Unsichtbarer Anker oben im Thread. Scrollt er in den sichtbaren Bereich,
 * werden ältere Nachrichten nachgeladen (siehe useLoadOlder).
 */
export function LoadOlderSentinel({ hasMore, onLoadMore, visibleCount }: Props) {
  const sentinelRef = useLoadOlder(hasMore, onLoadMore, visibleCount)
  if (!hasMore) return null
  return (
    <div ref={sentinelRef} className="flex items-center justify-center py-3 text-xs text-[#8d9ab0]">
      <Loader2 size={12} className="mr-2 animate-spin" />
      Ältere Nachrichten werden geladen …
    </div>
  )
}
