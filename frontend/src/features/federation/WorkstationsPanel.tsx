import { useEffect, useState } from "react"
import type { CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { Globe } from "lucide-react"
import { federationApi } from "./api"
import type { Workstation } from "./types"
import { rgbFor } from "@/shared/colors"
import { WorkstationCard } from "./_WorkstationCard"
import { AddWorkstationDialog } from "./_AddDialog"

interface Props {
  /** Hinzufügen-Dialog offen? Der Knopf dafür sitzt im Kopf der Seite bzw. des Fensters. */
  showAdd: boolean
  onShowAdd: (open: boolean) => void
}

/** Workstation-Teil der Föderation: Info, Liste, Leer-Zustand, Hinzufügen-Dialog.
 *  Genutzt vom Föderations-Fenster (FederationOverlay, auch über die alte Adresse /federation). */
export function WorkstationsPanel({ showAdd, onShowAdd }: Props) {
  const { t } = useTranslation("federation")
  const [workstations, setWorkstations] = useState<Workstation[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      setWorkstations(await federationApi.list())
    } catch { /* ignore */ } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id: string) {
    if (!confirm(t("delete_confirm"))) return
    await federationApi.delete(id).catch(() => {})
    load()
  }

  async function handleToggle(id: string, enabled: boolean) {
    await federationApi.update(id, { enabled }).catch(() => {})
    load()
  }

  return (
    <div className="space-y-4">
      <div className="box overflow-hidden p-4 space-y-2" style={{ "--c": rgbFor("/federation") } as CSSProperties}>
        <p className="text-xs text-zinc-500">
          {t("info_p1")}
          <code className="text-violet-400">ask_agent("persona@name", …)</code>
          {t("info_p2")}
          <code className="text-zinc-400">PROJEKTX_REMOTE_TOKEN</code>
          {t("info_p3")}
        </p>
      </div>

      {loading ? (
        <div className="text-sm text-zinc-500 py-8 text-center">{t("loading")}</div>
      ) : workstations.length === 0 ? (
        <div className="rounded-xl border border-white/[4%] bg-zinc-950/30 py-12 text-center">
          <Globe size={32} className="text-zinc-700 mx-auto mb-3" />
          <p className="text-sm text-zinc-500">{t("empty")}</p>
          <button
            onClick={() => onShowAdd(true)}
            className="mt-3 text-xs text-violet-400 hover:text-violet-300 transition-colors"
          >
            {t("add_first")}
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          {workstations.map(ws => (
            <WorkstationCard
              key={ws.id}
              ws={ws}
              onRefresh={load}
              onDelete={handleDelete}
              onToggle={handleToggle}
            />
          ))}
        </div>
      )}

      {showAdd && (
        <AddWorkstationDialog
          onClose={() => onShowAdd(false)}
          onCreated={() => { onShowAdd(false); load() }}
        />
      )}
    </div>
  )
}
