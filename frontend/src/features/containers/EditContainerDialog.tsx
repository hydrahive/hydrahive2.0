import { useId, useState } from "react"
import { Loader2, Save } from "lucide-react"
import { useTranslation } from "react-i18next"
import {
  AdminAction,
  AdminDialog,
  AdminFeedback,
  AdminField,
  AdminToggle,
  adminInputClass,
} from "@/features/cockpit/admin/ui"
import type { Container } from "./types"
import { containersApi } from "./api"

interface Props {
  container: Container
  onClose: () => void
  onSaved: () => void
}

export function EditContainerDialog({ container, onClose, onSaved }: Props) {
  const { t } = useTranslation("containers")
  const formId = useId()
  const editable = container.actual_state === "stopped" || container.actual_state === "created" || container.actual_state === "error"
  const [name, setName] = useState(container.name)
  const [description, setDescription] = useState(container.description ?? "")
  const [cpuSet, setCpuSet] = useState(container.cpu !== null && container.cpu !== undefined)
  const [cpu, setCpu] = useState(container.cpu ?? 2)
  const [ramSet, setRamSet] = useState(container.ram_mb !== null && container.ram_mb !== undefined)
  const [ramMb, setRamMb] = useState(container.ram_mb ?? 1024)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const validName = /^[a-zA-Z][a-zA-Z0-9-]{0,62}$/.test(name)
  const origCpuSet = container.cpu !== null && container.cpu !== undefined
  const origRamSet = container.ram_mb !== null && container.ram_mb !== undefined
  const dirty = name !== container.name
    || description !== (container.description ?? "")
    || cpuSet !== origCpuSet || (cpuSet && cpu !== container.cpu)
    || ramSet !== origRamSet || (ramSet && ramMb !== container.ram_mb)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!validName) { setError(t("create.error_name_invalid")); return }
    setBusy(true)
    setError(null)
    try {
      const patch: Parameters<typeof containersApi.update>[1] = {}
      if (name !== container.name) patch.name = name
      if (description !== (container.description ?? "")) patch.description = description.trim() || null
      if (cpuSet !== origCpuSet) {
        if (cpuSet) patch.cpu = cpu
        else patch.clear_cpu = true
      } else if (cpuSet && cpu !== container.cpu) {
        patch.cpu = cpu
      }
      if (ramSet !== origRamSet) {
        if (ramSet) patch.ram_mb = ramMb
        else patch.clear_ram = true
      } else if (ramSet && ramMb !== container.ram_mb) {
        patch.ram_mb = ramMb
      }
      await containersApi.update(container.container_id, patch)
      onSaved()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("edit.error"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AdminDialog
      eyebrow="Admin · Container"
      title={`Container bearbeiten: ${container.name}`}
      icon={<Save size={16} />}
      onClose={busy ? undefined : onClose}
      maxWidthClass="max-w-lg"
      footer={(
        <>
          <AdminAction onClick={onClose} disabled={busy}>Abbrechen</AdminAction>
          <AdminAction type="submit" form={formId} tone="primary" disabled={!editable || !dirty || busy}>
            {busy ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            Speichern
          </AdminAction>
        </>
      )}
    >
      <form id={formId} onSubmit={submit} className="space-y-4">
        {!editable && (
          <AdminFeedback tone="warning">
            Container muss gestoppt sein zum Bearbeiten. Aktuell: <strong>{container.actual_state}</strong>
          </AdminFeedback>
        )}

        <AdminField label={t("edit.field_name")}>
          <input value={name} onChange={(event) => setName(event.target.value)} disabled={!editable} className={adminInputClass} />
        </AdminField>
        <AdminField label={t("edit.field_desc")}>
          <input value={description} onChange={(event) => setDescription(event.target.value)} disabled={!editable} className={adminInputClass} />
        </AdminField>
        <AdminField label={t("edit.field_image_readonly")}>
          <input value={container.image} disabled className={`${adminInputClass} cursor-not-allowed font-mono`} />
        </AdminField>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-2 rounded-[4px] border border-[#2a364b] bg-[#111827] p-3">
            <AdminToggle label={t("edit.field_cpu")} checked={cpuSet}
              onChange={(event) => setCpuSet(event.target.checked)} disabled={!editable} />
            <AdminField label={cpuSet ? t("edit.field_cpu") : "unbegrenzt"}>
              <input type="number" min={1} max={64} value={cpu} disabled={!editable || !cpuSet}
                onChange={(event) => setCpu(parseInt(event.target.value, 10) || 1)} className={adminInputClass} />
            </AdminField>
          </div>
          <div className="space-y-2 rounded-[4px] border border-[#2a364b] bg-[#111827] p-3">
            <AdminToggle label={t("edit.field_ram")} checked={ramSet}
              onChange={(event) => setRamSet(event.target.checked)} disabled={!editable} />
            <AdminField label={ramSet ? t("edit.field_ram") : "unbegrenzt"}>
              <input type="number" min={64} max={32768} step={64} value={ramMb} disabled={!editable || !ramSet}
                onChange={(event) => setRamMb(parseInt(event.target.value, 10) || 64)} className={adminInputClass} />
            </AdminField>
          </div>
        </div>

        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      </form>
    </AdminDialog>
  )
}
