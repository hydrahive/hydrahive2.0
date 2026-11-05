import { useEffect, useState } from "react"
import { LogOut, Settings, Shield, User, X } from "lucide-react"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { getInstanceIdentity } from "./instanceIdentity"

const go = (path: string) => window.open(path, "_self")

const BUTTON_BASE = "flex max-w-[150px] items-center gap-2 overflow-hidden rounded-[4px] border bg-s-innen text-left text-xs font-bold"
const NORMAL_BUTTON = "border-s-rand px-2.5 py-1.5 text-[#e8eef8] hover:border-s-rand-hover"
const ADMIN_BUTTON = "border-amber-500/70 bg-amber-500/10 px-2.5 py-1.5 text-amber-200 hover:border-amber-300"

export function CockpitUserMenu({ compact = false }: { compact?: boolean }) {
  const [open, setOpen] = useState(false)
  const username = useAuthStore((state) => state.username)
  const role = useAuthStore((state) => state.role)
  const logout = useAuthStore((state) => state.logout)
  const identity = getInstanceIdentity(username, role)
  const buttonClassName = [
    BUTTON_BASE,
    identity.isSystemAccount ? ADMIN_BUTTON : NORMAL_BUTTON,
    compact ? "w-full max-w-none px-3 py-2" : "",
  ].filter(Boolean).join(" ")

  useEffect(() => {
    if (!open) return
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false) }
    window.addEventListener("keydown", close)
    return () => window.removeEventListener("keydown", close)
  }, [open])

  function signOut() {
    logout()
    go("/login")
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((value) => !value)}
        aria-label={identity.buttonLabel}
        title={identity.buttonLabel}
        aria-expanded={open}
        aria-controls="cockpit-user-menu"
        data-instance-identity={identity.isSystemAccount ? "system-admin" : identity.isAdministrator ? "administrator" : "user"}
        className={buttonClassName}
      >
        <span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full ${identity.isSystemAccount ? "bg-amber-500/20 text-amber-300" : "bg-s-hebung text-[#69d7ff]"}`}>
          {identity.isAdministrator ? <Shield size={13} /> : <User size={13} />}
        </span>
        <span className="min-w-0 max-w-[104px]">
          <span className="block truncate">{identity.username}</span>
          <span className={`block truncate text-[10px] font-semibold ${identity.isSystemAccount ? "text-amber-300" : "text-[#9aa7bc]"}`}>
            {identity.roleBadge} · {identity.shortHost}
          </span>
        </span>
      </button>

      {open && (
        <>
          <button className="fixed inset-0 z-[119] cursor-default" aria-label="Benutzermenü schließen" onClick={() => setOpen(false)} />
          <section id="cockpit-user-menu" aria-label={identity.buttonLabel} className="fixed inset-x-3 top-[68px] z-[120] rounded-[6px] border border-s-rand bg-s-box p-2 shadow-2xl sm:absolute sm:inset-x-auto sm:right-0 sm:top-14 sm:w-64">
            <header className="flex items-center justify-between border-b border-s-rand px-2 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-[#e8eef8]">{identity.username}</p>
                <p className={`text-[10px] uppercase tracking-wider ${identity.isSystemAccount ? "text-amber-300" : "text-[#9aa7bc]"}`}>{identity.roleLabel} · {identity.host}</p>
              </div>
              <button onClick={() => setOpen(false)} className="rounded p-1.5 text-[#9aa7bc] hover:bg-white/5 hover:text-white" aria-label="Benutzermenü schließen"><X size={15} /></button>
            </header>
            {identity.systemAccountWarning && <p role="note" className="mx-2 mt-2 rounded border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 text-[11px] leading-relaxed text-amber-200">{identity.systemAccountWarning}</p>}
            <button onClick={() => go("/profile")} className="mt-1 flex w-full items-center gap-2 rounded px-2 py-2 text-left text-xs text-[#b8c4d8] hover:bg-s-hebung hover:text-white"><User size={14} />Profil</button>
            <button onClick={() => go("/settings")} className="flex w-full items-center gap-2 rounded px-2 py-2 text-left text-xs text-[#b8c4d8] hover:bg-s-hebung hover:text-white"><Settings size={14} />Meine Einstellungen</button>
            <button onClick={signOut} className="flex w-full items-center gap-2 rounded px-2 py-2 text-left text-xs text-rose-300 hover:bg-rose-500/10"><LogOut size={14} />Abmelden</button>
          </section>
        </>
      )}
    </div>
  )
}
