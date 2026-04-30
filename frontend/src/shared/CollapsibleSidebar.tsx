import { useState } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"

interface CollapsibleSidebarProps {
  children: React.ReactNode
}

export function CollapsibleSidebar({ children }: CollapsibleSidebarProps) {
  // Default: auf Mobile (<lg, 1024px) eingeklappt, auf Desktop ausgeklappt.
  const [open, setOpen] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth >= 1024 : true
  )

  return (
    <>
      {/* Toggle Button - fixed am rechten Viewport-Rand */}
      <button
        onClick={() => setOpen(!open)}
        className={`fixed top-20 z-50 flex items-center justify-center w-6 h-12 rounded-l-lg bg-zinc-800/90 border border-white/10 border-r-0 shadow-lg transition-all duration-300 ${
          open ? "right-[18rem]" : "right-0"
        }`}
        title={open ? "Seitenleiste verstecken" : "Seitenleiste anzeigen"}
      >
        {open ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>

      {/* Collapsible Sidebar - Teil des Layouts, NICHT fixed! */}
      <aside
        className={`flex-shrink-0 border-l border-white/[6%] bg-white/[2%] transition-all duration-300 ${
          open ? "w-72" : "w-0 overflow-hidden"
        }`}
      >
        {/* Content bleibt gemounted */}
        <div className={`h-full ${open ? "visible" : "invisible"}`}>
          {children}
        </div>
      </aside>
    </>
  )
}
