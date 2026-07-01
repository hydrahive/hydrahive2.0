import type { CSSProperties } from "react"
import { useEffect, useRef, useState } from "react"
import { AlertTriangle, Loader2, Server, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { rgbFor } from "@/shared/colors"
import { ModalPortal } from "@/shared/ModalPortal"
import { systemApi, type MigrationStartBody } from "./api"

type Phase = "form" | "running" | "done" | "failed"

export function MigrationModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("system")
  const [phase, setPhase] = useState<Phase>("form")
  const [host, setHost] = useState("")
  const [port, setPort] = useState("22")
  const [sshUser, setSshUser] = useState("root")
  const [password, setPassword] = useState("")
  const [bwlimit, setBwlimit] = useState("0")
  const [error, setError] = useState<string | null>(null)
  const [log, setLog] = useState<string[]>([])
  const logRef = useRef<HTMLDivElement>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  useEffect(() => {
    logRef.current?.scrollTo(0, logRef.current.scrollHeight)
  }, [log])

  function startPolling() {
    if (pollRef.current) clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const r = await systemApi.migrationLog(500)
        setLog(r.lines)
        if (!r.running) {
          if (pollRef.current) clearInterval(pollRef.current)
          const st = await systemApi.migrationStatus()
          setPhase(st.last_result?.ok ? "done" : "failed")
        }
      } catch { /* transient — weiter pollen */ }
    }, 2000)
  }

  async function handleStart() {
    if (!host.trim() || !password) return
    setError(null)
    const body: MigrationStartBody = {
      host: host.trim(),
      port: Number(port) || 22,
      ssh_user: sshUser.trim() || "root",
      password,
      bwlimit_kbps: Number(bwlimit) || 0,
    }
    try {
      await systemApi.migrationStart(body)
      setPassword("")   // Klartext nicht länger im State halten
      setPhase("running")
      setLog([])
      startPolling()
    } catch (e) {
      const err = e as { detail_code?: string; message?: string }
      setError(err.detail_code ? t(`migration.err.${err.detail_code}`, err.detail_code) : (err.message || String(e)))
    }
  }

  return (
    <ModalPortal>
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onClick={(e) => { if (e.target === e.currentTarget && phase !== "running") onClose() }}>
      <div className="box box-static overflow-hidden w-full max-w-2xl flex flex-col max-h-[85vh]"
        style={{ "--c": rgbFor("/system") } as CSSProperties}>
        <div className="flex items-center justify-between gap-3 px-5 py-3 border-b border-white/[8%] flex-shrink-0">
          <div className="flex items-center gap-2">
            <Server size={15} className="text-violet-300" />
            <p className="text-sm font-semibold text-zinc-100">{t("migration.title")}</p>
          </div>
          {phase !== "running" && (
            <button onClick={onClose} className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%]">
              <X size={16} />
            </button>
          )}
        </div>

        <div className="p-5 space-y-4 overflow-y-auto">
          {phase === "form" && (
            <>
              <div className="flex items-start gap-2 rounded-lg bg-amber-500/[7%] border border-amber-500/25 p-3">
                <AlertTriangle size={15} className="text-amber-300 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-amber-100/90 leading-relaxed">{t("migration.warning")}</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <label className="sm:col-span-2 space-y-1">
                  <span className="text-[11px] uppercase tracking-wider text-zinc-500">{t("migration.host")}</span>
                  <input value={host} onChange={(e) => setHost(e.target.value)}
                    placeholder="192.168.178.121"
                    className="w-full px-3 py-2 rounded-lg bg-black/30 border border-white/10 text-sm text-zinc-100 focus:border-violet-500/50 outline-none" />
                </label>
                <label className="space-y-1">
                  <span className="text-[11px] uppercase tracking-wider text-zinc-500">{t("migration.port")}</span>
                  <input value={port} onChange={(e) => setPort(e.target.value)} inputMode="numeric"
                    className="w-full px-3 py-2 rounded-lg bg-black/30 border border-white/10 text-sm text-zinc-100 focus:border-violet-500/50 outline-none" />
                </label>
                <label className="space-y-1">
                  <span className="text-[11px] uppercase tracking-wider text-zinc-500">{t("migration.user")}</span>
                  <input value={sshUser} onChange={(e) => setSshUser(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-black/30 border border-white/10 text-sm text-zinc-100 focus:border-violet-500/50 outline-none" />
                </label>
                <label className="sm:col-span-2 space-y-1">
                  <span className="text-[11px] uppercase tracking-wider text-zinc-500">{t("migration.password")}</span>
                  <input value={password} onChange={(e) => setPassword(e.target.value)} type="password"
                    autoComplete="off"
                    className="w-full px-3 py-2 rounded-lg bg-black/30 border border-white/10 text-sm text-zinc-100 focus:border-violet-500/50 outline-none" />
                </label>
                <label className="sm:col-span-3 space-y-1">
                  <span className="text-[11px] uppercase tracking-wider text-zinc-500">{t("migration.bwlimit")}</span>
                  <input value={bwlimit} onChange={(e) => setBwlimit(e.target.value)} inputMode="numeric"
                    className="w-full px-3 py-2 rounded-lg bg-black/30 border border-white/10 text-sm text-zinc-100 focus:border-violet-500/50 outline-none" />
                </label>
              </div>

              {error && <p className="text-xs text-red-400">{error}</p>}

              <div className="flex justify-end gap-2 pt-1">
                <button onClick={onClose}
                  className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-zinc-200 hover:bg-white/[5%] transition-colors">
                  {t("migration.cancel")}
                </button>
                <button onClick={handleStart} disabled={!host.trim() || !password}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-violet-500/15 border border-violet-500/30 text-violet-200 text-xs font-medium hover:bg-violet-500/25 disabled:opacity-40 transition-colors">
                  <Server size={12} /> {t("migration.start")}
                </button>
              </div>
            </>
          )}

          {phase !== "form" && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm">
                {phase === "running" && <><Loader2 size={14} className="animate-spin text-violet-300" /><span className="text-zinc-300">{t("migration.running")}</span></>}
                {phase === "done" && <span className="text-emerald-300">{t("migration.success")}</span>}
                {phase === "failed" && <span className="text-red-400">{t("migration.failure")}</span>}
              </div>
              <div ref={logRef}
                className="h-72 overflow-y-auto rounded-lg bg-black/50 border border-white/10 p-3 font-mono text-[11px] leading-relaxed text-zinc-400 whitespace-pre-wrap">
                {log.length === 0 ? t("migration.log_wait") : log.join("")}
              </div>
              {phase !== "running" && (
                <div className="flex justify-end">
                  <button onClick={onClose}
                    className="px-3 py-1.5 rounded-lg bg-white/[6%] border border-white/10 text-xs text-zinc-200 hover:bg-white/[10%] transition-colors">
                    {t("migration.close")}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
    </ModalPortal>
  )
}
