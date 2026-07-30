import { useState } from "react"
import { ChevronUp, Loader2 } from "lucide-react"
import { useLoadOlder } from "./_useLoadOlder"

interface Props {
  hasMore: boolean
  onLoadMore: () => void
  /** Sichtbare Nachrichtenanzahl — treibt Scroll-Korrektur nach dem Nachladen. */
  visibleCount: number
}

/**
 * Anker oben im Thread. Scrollt er in den sichtbaren Bereich, werden ältere
 * Nachrichten nachgeladen (siehe useLoadOlder).
 *
 * Zeigt einen echten Ruhezustand: vorher stand hier dauerhaft „Ältere
 * Nachrichten werden geladen …“, solange überhaupt noch ältere existierten —
 * auch wenn gerade nichts lud. Das war als Dauer-Hänger missverständlich.
 * Der Spinner erscheint jetzt nur zwischen Auslösen und Eintreffen.
 *
 * Zusätzlich ist der Anker klickbar: Falls der Scroll-Container nicht
 * auflösbar ist (exotisches Layout), bleibt Nachladen so trotzdem möglich.
 */
export function LoadOlderSentinel({ hasMore, onLoadMore, visibleCount }: Props) {
  // Zustand als "wofür wurde geladen" statt als boolean: sobald visibleCount
  // sich ändert (Nachschub da) oder hasMore wegfällt, ist der Spinner
  // automatisch vorbei — ohne setState-im-Effekt und ohne Hänger-Risiko,
  // wenn ein Ladevorgang folgenlos bleibt.
  const [pendingAt, setPendingAt] = useState<number | null>(null)
  const loading = hasMore && pendingAt === visibleCount

  const handleLoadMore = () => {
    setPendingAt(visibleCount)
    onLoadMore()
  }

  const sentinelRef = useLoadOlder(hasMore, handleLoadMore, visibleCount)

  if (!hasMore) return null
  return (
    <div ref={sentinelRef} className="flex items-center justify-center py-3">
      <button
        type="button"
        onClick={handleLoadMore}
        disabled={loading}
        className="flex items-center gap-2 rounded-[4px] px-2 py-1 text-xs text-[#8d9ab0] transition-colors hover:bg-white/[6%] hover:text-[#e8eef8] disabled:cursor-default disabled:hover:bg-transparent"
      >
        {loading ? (
          <>
            <Loader2 size={12} className="animate-spin" />
            Ältere Nachrichten werden geladen …
          </>
        ) : (
          <>
            <ChevronUp size={12} />
            Ältere Nachrichten laden
          </>
        )}
      </button>
    </div>
  )
}
