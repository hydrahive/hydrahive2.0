import { useEffect, useState, type ComponentType } from "react"
import { Box, Cpu, MemoryStick, Network, Pencil, Play, RotateCw, Server, Square, Terminal, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import {
  AdminAction,
  AdminConfirmDialog,
  AdminFeedback,
  AdminPanel,
} from "@/features/cockpit/admin/ui"
import type { Container, ContainerInfo } from "./types"
import { ContainerStatusBadge } from "./StatusBadge"
import { ContainerConsoleModal } from "./ContainerConsoleModal"
import { containersApi } from "./api"

interface Props {
  container: Container
  onStart: () => Promise<void>
  onStop: () => Promise<void>
  onRestart: () => Promise<void>
  onDelete: () => Promise<void>
  onEdit: () => void
  onOpenDetail: () => void
}

export function ContainerCard({ container, onStart, onStop, onRestart, onDelete, onEdit, onOpenDetail }: Props) {
  const { t } = useTranslation("containers")
  const { t: tCommon } = useTranslation("common")
  const [busy, setBusy] = useState(false)
  const [info, setInfo] = useState<ContainerInfo | null>(null)
  const [showConsole, setShowConsole] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  async function withBusy(action: () => Promise<void>) {
    if (busy) return
    setBusy(true)
    setActionError(null)
    try {
      await action()
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (container.actual_state !== "running") {
      const clear = window.setTimeout(() => setInfo(null), 0)
      return () => window.clearTimeout(clear)
    }
    let active = true
    async function tick() {
      try {
        const nextInfo = await containersApi.info(container.container_id)
        if (active) setInfo(nextInfo)
      } catch { /* Die Card behält beim Polling den letzten bekannten Wert. */ }
    }
    void tick()
    const interval = window.setInterval(tick, 4000)
    return () => { active = false; window.clearInterval(interval) }
  }, [container.container_id, container.actual_state])

  const running = container.actual_state === "running"
  const transitioning = container.actual_state === "starting" || container.actual_state === "stopping"
  const canStart = container.actual_state === "stopped" || container.actual_state === "error"
  const memoryMb = info?.memory_bytes == null ? null : Math.round(info.memory_bytes / 1024 / 1024)
  const memoryPercent = memoryMb != null && container.ram_mb ? Math.min(100, memoryMb / container.ram_mb * 100) : null

  return (
    <>
      <AdminPanel
        icon={Box}
        title={<button type="button" onClick={onOpenDetail} className="truncate text-left hover:text-[#69d7ff] hover:underline">{container.name}</button>}
        description={container.description || container.image}
        actions={<ContainerStatusBadge state={container.actual_state} />}
        bodyClassName="space-y-3"
      >
        {container.description && <p className="truncate font-mono text-[11px] text-[#5b6675]">{container.image}</p>}

        <div className="flex flex-wrap gap-2 text-[11px]">
          <Spec icon={Cpu} label={container.cpu ? `${container.cpu} vCPU` : t("spec.cpu_unlimited")} />
          <Spec icon={MemoryStick} label={container.ram_mb ? `${container.ram_mb} MB` : t("spec.ram_unlimited")} />
          <Spec icon={Network} label={container.network_mode} />
          {container.node_id !== "local" && <Spec icon={Server} label={container.node_id} accent />}
          {info?.ipv4 && <Spec label={info.ipv4} accent />}
        </div>

        {info?.alive && memoryMb != null && container.ram_mb && (
          <div className="text-[11px] text-[#8d9ab0]">
            <div className="flex items-baseline justify-between">
              <span>RAM</span>
              <span className="font-mono">{memoryMb} / {container.ram_mb} MB</span>
            </div>
            <div className="mt-1 h-1 overflow-hidden rounded-full bg-[#0b111c]">
              <div className="h-full bg-[#69d7ff] transition-all" style={{ width: `${memoryPercent ?? 0}%` }} />
            </div>
          </div>
        )}

        {container.last_error_code && container.actual_state === "error" && <AdminFeedback tone="danger">{container.last_error_code}</AdminFeedback>}
        {actionError && <AdminFeedback tone="danger">{actionError}</AdminFeedback>}

        <div className="flex flex-wrap items-center gap-2 pt-1">
          {canStart && <AdminAction tone="primary" disabled={busy || transitioning} onClick={() => withBusy(onStart)}><Play size={12} />Start</AdminAction>}
          {running && (
            <>
              <AdminAction disabled={busy} onClick={() => setShowConsole(true)}><Terminal size={12} />Console</AdminAction>
              <AdminAction disabled={busy || transitioning} onClick={() => withBusy(onRestart)}><RotateCw size={12} />Restart</AdminAction>
              <AdminAction disabled={busy || transitioning} onClick={() => withBusy(onStop)}><Square size={12} />Stop</AdminAction>
            </>
          )}
          <div className="flex-1" />
          {!running && !transitioning && <AdminAction tone="ghost" className="px-2" onClick={onEdit} title="Bearbeiten" aria-label="Bearbeiten"><Pencil size={12} /></AdminAction>}
          {!running && !transitioning && <AdminAction tone="danger" className="px-2" disabled={busy} onClick={() => setConfirmDelete(true)} title="Löschen" aria-label="Löschen"><Trash2 size={12} /></AdminAction>}
        </div>
      </AdminPanel>

      {showConsole && <ContainerConsoleModal container={container} onClose={() => setShowConsole(false)} />}
      {confirmDelete && (
        <AdminConfirmDialog
          title="Container löschen"
          confirmLabel="Löschen"
          cancelLabel={tCommon("actions.cancel")}
          onClose={() => setConfirmDelete(false)}
          onConfirm={async () => { await withBusy(onDelete); setConfirmDelete(false) }}
          busy={busy}
        >
          Container „{container.name}“ wirklich löschen? Die Daten werden dauerhaft entfernt.
        </AdminConfirmDialog>
      )}
    </>
  )
}

function Spec({ icon: Icon, label, accent = false }: { icon?: ComponentType<{ size?: number; className?: string }>; label: string; accent?: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-[4px] border px-2 py-1 ${accent ? "border-[#69d7ff]/35 bg-[#163248] text-[#c8f2ff]" : "border-[#2a364b] bg-[#0d1420] text-[#8d9ab0]"}`}>
      {Icon && <Icon size={11} />}{label}
    </span>
  )
}
