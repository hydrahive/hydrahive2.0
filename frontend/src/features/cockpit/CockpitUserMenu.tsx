import { useState } from "react"
import { LogOut, Settings, User, X } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"

const go = (path: string) => window.open(path, "_self")

export function CockpitUserMenu({ compact = false }: { compact?: boolean }) {
  const [open, setOpen] = useState(false)
  const username = useAuthStore((state) => state.username) ?? "User"
  const role = useAuthStore((state) => state.role) ?? "user"
  const logout = useAuthStore((state) => state.logout)

  function signOut() {
    logout()
    go("/login")
  }

  return <div className="relative">
    <button onClick={() => setOpen((value) => !value)} aria-expanded={open} aria-controls="cockpit-user-menu" className={compact ? "flex w-full items-center gap-2 rounded-[4px] border border-[#2a364b] bg-[#172133] px-3 py-2 text-left text-xs font-bold text-[#e8eef8]" : "flex items-center gap-2 rounded-[4px] border border-[#2a364b] bg-[#172133] px-2.5 py-1.5 text-xs font-bold text-[#e8eef8] hover:border-[#46617f]"}><span className="grid h-6 w-6 place-items-center rounded-full bg-[#27354c] text-[#69d7ff]"><User size={13} /></span><span className="max-w-24 truncate">{username}</span></button>
    {open && <><button className="fixed inset-0 z-[119] cursor-default" aria-label="Benutzermenü schließen" onClick={() => setOpen(false)} /><section id="cockpit-user-menu" role="menu" className="fixed inset-x-3 top-[68px] z-[120] rounded-[6px] border border-[#2a364b] bg-[#101724] p-2 shadow-2xl sm:absolute sm:inset-x-auto sm:right-0 sm:top-11 sm:w-64"><header className="flex items-center justify-between border-b border-[#2a364b] px-2 py-2"><div className="min-w-0"><p className="truncate text-sm font-semibold text-[#e8eef8]">{username}</p><p className="text-[10px] uppercase tracking-wider text-[#718097]">{role}</p></div><button onClick={() => setOpen(false)} className="rounded p-1.5 text-[#8d9ab0] hover:bg-white/5 hover:text-white" aria-label="Benutzermenü schließen"><X size={15} /></button></header><button role="menuitem" onClick={() => go("/profile")} className="mt-1 flex w-full items-center gap-2 rounded px-2 py-2 text-left text-xs text-[#b8c4d8] hover:bg-[#172133] hover:text-white"><User size={14} />Profil</button><button role="menuitem" onClick={() => go("/settings")} className="flex w-full items-center gap-2 rounded px-2 py-2 text-left text-xs text-[#b8c4d8] hover:bg-[#172133] hover:text-white"><Settings size={14} />Einstellungen</button><button role="menuitem" onClick={signOut} className="flex w-full items-center gap-2 rounded px-2 py-2 text-left text-xs text-rose-300 hover:bg-rose-500/10"><LogOut size={14} />Abmelden</button></section></>}
  </div>
}
