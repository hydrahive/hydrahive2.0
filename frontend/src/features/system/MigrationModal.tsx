import { useEffect, useRef, useState } from "react"
import { Server } from "lucide-react"
import { useTranslation } from "react-i18next"
import {
  AdminAction,
  AdminCodeBlock,
  AdminDialog,
  AdminFeedback,
  AdminField,
  adminInputClass,
} from "@/features/cockpit/admin/ui"
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
        const response = await systemApi.migrationLog(500)
        setLog(response.lines)
        if (!response.running) {
          if (pollRef.current) clearInterval(pollRef.current)
          const status = await systemApi.migrationStatus()
          setPhase(status.last_result?.ok ? "done" : "failed")
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
      setPassword("") // Klartext nicht länger im State halten
      setPhase("running")
      setLog([])
      startPolling()
    } catch (e) {
      const err = e as { detail_code?: string; message?: string }
      setError(err.detail_code ? t(`migration.err.${err.detail_code}`, err.detail_code) : (err.message || String(e)))
    }
  }

  const dismissable = phase !== "running"
  const footer = phase === "form" ? (
    <>
      <AdminAction onClick={onClose}>{t("migration.cancel")}</AdminAction>
      <AdminAction onClick={handleStart} disabled={!host.trim() || !password} tone="primary">
        <Server size={12} /> {t("migration.start")}
      </AdminAction>
    </>
  ) : dismissable ? (
    <AdminAction onClick={onClose} tone="primary">{t("migration.close")}</AdminAction>
  ) : undefined

  return (
    <AdminDialog
      eyebrow="System · Migration"
      title={t("migration.title")}
      icon={<Server size={16} />}
      onClose={dismissable ? onClose : undefined}
      footer={footer}
    >
      {phase === "form" && (
        <div className="space-y-4">
          <AdminFeedback tone="warning">{t("migration.warning")}</AdminFeedback>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <AdminField label={t("migration.host")} className="sm:col-span-2">
              <input
                value={host}
                onChange={(event) => setHost(event.target.value)}
                placeholder="192.168.178.121"
                className={adminInputClass}
              />
            </AdminField>
            <AdminField label={t("migration.port")}>
              <input value={port} onChange={(event) => setPort(event.target.value)} inputMode="numeric" className={adminInputClass} />
            </AdminField>
            <AdminField label={t("migration.user")}>
              <input value={sshUser} onChange={(event) => setSshUser(event.target.value)} className={adminInputClass} />
            </AdminField>
            <AdminField label={t("migration.password")} className="sm:col-span-2">
              <input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="off"
                className={adminInputClass}
              />
            </AdminField>
            <AdminField label={t("migration.bwlimit")} className="sm:col-span-3">
              <input value={bwlimit} onChange={(event) => setBwlimit(event.target.value)} inputMode="numeric" className={adminInputClass} />
            </AdminField>
          </div>

          {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
        </div>
      )}

      {phase !== "form" && (
        <div className="space-y-3">
          {phase === "running" && <AdminFeedback tone="warning" loading>{t("migration.running")}</AdminFeedback>}
          {phase === "done" && <AdminFeedback tone="success">{t("migration.success")}</AdminFeedback>}
          {phase === "failed" && <AdminFeedback tone="danger">{t("migration.failure")}</AdminFeedback>}
          <div ref={logRef} className="h-72 overflow-y-auto">
            <AdminCodeBlock className="min-h-72">
              {log.length === 0 ? t("migration.log_wait") : log.join("")}
            </AdminCodeBlock>
          </div>
        </div>
      )}
    </AdminDialog>
  )
}
