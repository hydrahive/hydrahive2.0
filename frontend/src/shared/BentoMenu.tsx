import { useEffect, useRef } from "react"
import { Link, useLocation } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { Grip } from "lucide-react"
import { visibleItems } from "./nav-config"
import { useAuthStore } from "@/features/auth/useAuthStore"

interface Props {
  open: boolean
  onClose: () => void
}

export function BentoMenu({ open, onClose }: Props) {
  const { t } = useTranslation("nav")
  const role = useAuthStore((s) => s.role)
  const { pathname } = useLocation()
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!open) return
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose()
    }
    document.addEventListener("mousedown", onClick)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onClick)
      document.removeEventListener("keydown", onKey)
    }
  }, [open, onClose])

  if (!open) return null
  const items = visibleItems(role)

  return (
    <div className="fixed inset-0 z-40 flex items-start justify-end pt-14 pr-3 sm:pr-4 pointer-events-none">
      <div
        ref={ref}
        className="pointer-events-auto w-[min(95vw,360px)] max-h-[80vh] overflow-y-auto rounded-2xl border border-white/[10%] bg-zinc-950/95 backdrop-blur-xl shadow-2xl shadow-black/60 p-3"
      >
        <div className="flex items-center gap-2 px-2 pb-2 mb-2 border-b border-white/[6%]">
          <Grip size={13} className="text-zinc-500" />
          <p className="text-[11px] uppercase tracking-wider text-zinc-500 font-semibold">Apps</p>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {items.map(({ path, icon: Icon, labelKey }) => {
            const active = path === "/" ? pathname === "/" : pathname.startsWith(path)
            return (
              <Link
                key={path}
                to={path}
                onClick={onClose}
                className={`flex flex-col items-center gap-1.5 p-3 rounded-xl transition-colors ${
                  active
                    ? "bg-violet-500/15 border border-violet-500/30"
                    : "border border-transparent hover:bg-white/[5%]"
                }`}
              >
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                  active ? "bg-violet-500/20 text-violet-200" : "bg-white/[5%] text-zinc-300"
                }`}>
                  <Icon size={18} />
                </div>
                <span className={`text-[11px] text-center leading-tight ${
                  active ? "text-violet-200 font-medium" : "text-zinc-400"
                }`}>
                  {t(`items.${labelKey}`)}
                </span>
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  )
}
