import { useCallback, useEffect, useState } from "react"
import { ArrowRightLeft } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminDialog } from "@/features/cockpit/admin/ui"
import { addonsApi } from "@/features/system/addonsApi"
import { archiveApi, type ArchiveLocation } from "./api"
import { MoveView } from "./MoveView"

interface Props {
  onClose: () => void
  onStarted: () => void
}

/** Dialog „Archiv-Ort wechseln“: Platte wählen, ggf. für HydraHive einrichten, Umzug starten (Spec Etappe 1b). */
export function MoveDialog({ onClose, onStarted }: Props) {
  const { t } = useTranslation("archive")
  const [locations, setLocations] = useState<ArchiveLocation[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [preparing, setPreparing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try { setLocations((await archiveApi.locations()).entries); setError(null) }
    catch (e) { setError(e instanceof Error ? e.message : t("move.load_failed")) }
  }, [t])

  useEffect(() => {
    const first = setTimeout(() => { void load() }, 0)
    return () => clearTimeout(first)
  }, [load])

  async function move() {
    if (!selected) return
    setBusy(true); setError(null)
    try { await archiveApi.move(selected); onStarted() }
    catch (e) { setError(e instanceof Error ? e.message : t("move.error.unexpected")); setBusy(false) }
  }

  async function prepare() {
    if (!selected) return
    setPreparing(true); setError(null)
    try {
      await archiveApi.prepare(selected)
      // Läuft über den Root-Runner der Zusatz-Module. Fertig, sobald er nichts mehr bearbeitet;
      // ob es geklappt hat, zeigt die neu geladene Liste (Platte ohne „target_not_writable“).
      for (let i = 0; i < 60; i++) {
        await new Promise((resolve) => setTimeout(resolve, 2000))
        if ((await addonsApi.list()).running === null) break
      }
      const fresh = (await archiveApi.locations()).entries
      setLocations(fresh)
      if (fresh.find((l) => l.id === selected)?.problems.includes("target_not_writable")) setError(t("move.prepare_failed"))
    } catch (e) { setError(e instanceof Error ? e.message : t("move.prepare_failed")) }
    finally { setPreparing(false) }
  }

  return (
    <AdminDialog eyebrow={t("title")} title={t("move.title")} icon={<ArrowRightLeft size={15} />}
      onClose={onClose} maxWidthClass="max-w-xl">
      <MoveView locations={locations} selected={selected} busy={busy} preparing={preparing} error={error}
        onSelect={setSelected} onMove={() => void move()} onPrepare={() => void prepare()} />
    </AdminDialog>
  )
}
