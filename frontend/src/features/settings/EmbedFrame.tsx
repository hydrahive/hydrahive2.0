import { Suspense } from "react"
import { Loader2 } from "lucide-react"

/**
 * Bändigt Vollbild-Feature-Pages für die Einbettung im Settings-Hub.
 *
 * Diese Pages nutzen `-m-4 md:-m-6` (um das Outlet-Padding zu fressen) und
 * `h-[calc(100dvh-3rem)]` (volle Viewport-Höhe). Im eingebetteten ContentArea
 * würde das überlaufen. Dieser Frame:
 *  - gibt eine feste, an den Hub-Bereich angepasste Höhe (relativ zum Viewport
 *    minus Kopf/Tabs/Rahmen),
 *  - gleicht den negativen Außen-Margin der Page mit gleichem Padding aus,
 *  - kapselt das eigene Scrolling der Page.
 */
export function EmbedFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-[calc(100dvh-12rem)] overflow-hidden rounded-xl border border-white/8 bg-zinc-950/30">
      {/* p-4/p-6 gleicht das -m-4/-m-6 der eingebetteten Page aus → netto 0,
          aber die Page bekommt wieder ihren erwarteten Innenabstand. */}
      <div className="h-full overflow-hidden p-4 md:p-6">
        <Suspense fallback={
          <div className="flex h-full items-center justify-center">
            <Loader2 size={20} className="animate-spin text-zinc-500" />
          </div>
        }>
          {children}
        </Suspense>
      </div>
    </div>
  )
}
