import { useEffect, useMemo, useState } from "react"
import type { Message } from "./types"

const INITIAL_WINDOW = 50
const LOAD_STEP = 50

/**
 * Rendert nur die letzten N Nachrichten eines Threads statt aller. Ältere
 * werden beim Hochscrollen in Schritten nachgeladen. Das hält den DOM klein,
 * damit Re-Renders (Tippen, Streaming) auch in langen Sessions flüssig bleiben.
 *
 * `resetKey` (z.B. die Session-ID) setzt das Fenster zurück, sobald der Thread
 * wechselt — sonst würde eine kurze neue Session das Limit einer alten erben.
 */
export function useMessageWindow(messages: Message[], resetKey: string | null) {
  const [visibleCount, setVisibleCount] = useState(INITIAL_WINDOW)

  useEffect(() => {
    setVisibleCount(INITIAL_WINDOW)
  }, [resetKey])

  const total = messages.length
  const hasMore = total > visibleCount

  const windowed = useMemo(() => {
    if (!hasMore) return messages
    return messages.slice(total - visibleCount)
  }, [messages, hasMore, total, visibleCount])

  function loadMore() {
    setVisibleCount((c) => Math.min(c + LOAD_STEP, total))
  }

  return { windowed, hasMore, loadMore, visibleCount, total }
}
