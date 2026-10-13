import { useEffect, useState } from "react"
import { Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminDialog, AdminFeedback } from "@/features/cockpit/admin/ui"
import { deleteApi, findJob, initialMode, type DeleteJob, type DeleteKind, type DeleteMode, type DeletePreview } from "./api"
import { DeleteProgress } from "./DeleteProgress"
import { DeleteView } from "./DeleteView"

const POLL_MS = 1500

interface Props {
  kind: DeleteKind
  id: string
  onClose: () => void
  /** Beim Schließen, wenn der Auftrag fertig gelöscht hat (Liste neu laden). Erst dann – sonst
   *  verschwände der Dialog mit dem Objekt, bevor man das Ergebnis lesen kann. */
  onDeleted?: () => void
}

/** Ein Lösch-Dialog für Agent, Projekt, Nutzer und externe Instanz (Spec archiv-system.md, Etappe 2).
 *  Schließen ist jederzeit erlaubt – der Auftrag läuft im Hintergrund weiter. */
export function DeleteDialog({ kind, id, onClose, onDeleted }: Props) {
  const { t } = useTranslation("archive")
  const [preview, setPreview] = useState<DeletePreview | null>(null)
  const [mode, setMode] = useState<DeleteMode | null>(null)
  const [typed, setTyped] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [jobId, setJobId] = useState<string | null>(null)
  const [job, setJob] = useState<DeleteJob | null>(null)

  useEffect(() => {
    let alive = true
    deleteApi.preview(kind, id)
      .then((p) => { if (alive) { setPreview(p); setMode(initialMode(p)) } })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : t("delete.error.unexpected")) })
    return () => { alive = false }
  }, [kind, id, t])

  useEffect(() => {
    if (!jobId) return
    let alive = true
    const tick = async () => {
      try {
        const found = findJob(await deleteApi.jobs(), jobId)
        if (!alive || !found) return
        setJob(found)
        if (found.state === "done" || found.state === "failed") return
      } catch { /* nächster Versuch */ }
      if (alive) timer = setTimeout(() => { void tick() }, POLL_MS)
    }
    let timer = setTimeout(() => { void tick() }, 0)
    return () => { alive = false; clearTimeout(timer) }
  }, [jobId])

  const close = () => {
    if (job?.state === "done") onDeleted?.()
    onClose()
  }

  async function start() {
    if (!preview || !mode) return
    setBusy(true); setError(null)
    try { setJobId((await deleteApi.start(kind, id, mode, typed)).job_id) }
    catch (e) { setError(e instanceof Error ? e.message : t("delete.error.unexpected")); setBusy(false) }
  }

  return (
    <AdminDialog eyebrow={t(`delete.kind.${kind}`)} title={preview ? t("delete.title", { name: preview.name }) : t("delete.loading")}
      icon={<Trash2 size={15} />} onClose={close} maxWidthClass="max-w-xl">
      {!preview && !error && <div className="p-4"><AdminFeedback loading>{t("delete.loading")}</AdminFeedback></div>}
      {!preview && error && <div className="p-4"><AdminFeedback tone="danger">{error}</AdminFeedback></div>}
      {preview && !jobId && (
        <DeleteView preview={preview} mode={mode} typed={typed} busy={busy} error={error}
          onMode={(m) => { setMode(m); setTyped("") }} onTyped={setTyped} onStart={() => void start()} />
      )}
      {jobId && (
        <div className="space-y-2 p-4">
          {job ? <DeleteProgress job={job} /> : <AdminFeedback loading>{t("delete.step.queued")}</AdminFeedback>}
          {job?.state !== "done" && job?.state !== "failed" && <p className="text-xs text-[#8d9ab0]">{t("delete.close_ok")}</p>}
        </div>
      )}
    </AdminDialog>
  )
}
