import type { ReactNode } from "react"
import { BuddyDecorLayer } from "./_BuddyDecorLayer"
import type { BuddyDecorVariant } from "./api"

export function BuddyCockpitShell({
  leftRail,
  header,
  children,
  rightRail,
  bottomSlots,
  decorVariant,
  rightRailCollapsed,
}: {
  leftRail: ReactNode
  header: ReactNode
  children: ReactNode
  rightRail: ReactNode
  bottomSlots?: ReactNode
  decorVariant: BuddyDecorVariant
  rightRailCollapsed: boolean
}) {
  return (
    <div className="relative flex h-full min-h-0 w-full items-stretch gap-4 overflow-hidden px-0 py-0 sm:px-3 sm:py-3 xl:px-4 xl:py-4">
      <div className="hidden min-h-0 shrink-0 overflow-y-auto xl:block">{leftRail}</div>
      <main className="relative flex min-h-0 min-w-0 flex-1 flex-col border border-[#104E8B]/60 bg-[#1c2334]/90 shadow-2xl shadow-[0_0_50px_-12px_rgba(16,78,139,0.55)] backdrop-blur">
        <BuddyDecorLayer variant={decorVariant} />
        <div className="relative z-10 flex min-h-0 flex-1 flex-col">
          {header}
          {children}
          {bottomSlots && <div className="border-t border-white/[6%] bg-black/25 p-3 xl:hidden">{bottomSlots}</div>}
        </div>
      </main>
      {!rightRailCollapsed && (
        <aside className="hidden min-h-0 w-72 shrink-0 flex-col gap-3 overflow-y-auto xl:flex">{rightRail}</aside>
      )}
    </div>
  )
}
