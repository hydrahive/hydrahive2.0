import { useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { LogOut, User } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { LanguageSwitcher } from "@/i18n/LanguageSwitcher"

export function AvatarMenu() {
  const { username, role, logout } = useAuthStore()
  const { t } = useTranslation("auth")
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!open) return
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", onClick)
    return () => document.removeEventListener("mousedown", onClick)
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-violet-700 flex items-center justify-center text-white text-xs font-bold shadow-md shadow-violet-900/30 hover:scale-105 transition-transform"
        title={username ?? ""}
      >
        {username?.[0]?.toUpperCase() ?? "?"}
        <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-zinc-950" />
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-64 rounded-xl border border-white/[10%] bg-zinc-950/95 backdrop-blur-xl shadow-2xl shadow-black/60 z-50 overflow-hidden">
          <div className="px-4 py-3 border-b border-white/[6%]">
            <p className="text-sm font-medium text-zinc-100 truncate">{username}</p>
            <p className="text-[11px] text-zinc-500">{role}</p>
          </div>
          <div className="p-1.5">
            <Link
              to="/profile"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-zinc-300 hover:text-zinc-100 hover:bg-white/[5%]"
            >
              <User size={13} />
              <span>Profil</span>
            </Link>
          </div>
          <div className="px-3 py-2 border-t border-white/[6%]">
            <LanguageSwitcher />
          </div>
          <button
            onClick={() => { setOpen(false); logout() }}
            className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-rose-300 hover:bg-rose-500/10 border-t border-white/[6%]"
          >
            <LogOut size={13} />
            <span>{t("logout")}</span>
          </button>
        </div>
      )}
    </div>
  )
}
