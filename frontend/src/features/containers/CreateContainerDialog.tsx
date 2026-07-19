import { useEffect, useId, useState } from "react"
import { PackagePlus } from "lucide-react"
import { useTranslation } from "react-i18next"
import {
  AdminAction,
  AdminDialog,
  AdminFeedback,
  AdminField,
  adminInputClass,
} from "@/features/cockpit/admin/ui"
import { NodeSelector } from "@/features/nodes/NodeSelector"
import type { ContainerCreateInput, NetworkMode } from "./types"
import { containersApi } from "./api"
import { RadioCard } from "./_containerDialogHelpers"

interface Props {
  onClose: () => void
  onCreated: () => void
}

export function CreateContainerDialog({ onClose, onCreated }: Props) {
  const { t } = useTranslation("containers")
  const formId = useId()
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [image, setImage] = useState("debian/12")
  const [customImage, setCustomImage] = useState(false)
  const [cpu, setCpu] = useState<number | "">("")
  const [ramMb, setRamMb] = useState<number | "">("")
  const [network, setNetwork] = useState<NetworkMode>("bridged")
  const [nodeId, setNodeId] = useState("local")
  const [quickImages, setQuickImages] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    containersApi.quickImages()
      .then((images) => { if (active) setQuickImages(images) })
      .catch(() => { if (active) setQuickImages([]) })
    return () => { active = false }
  }, [])

  const validName = /^[a-zA-Z][a-zA-Z0-9-]{0,62}$/.test(name)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!validName) { setError(t("create.error_name_invalid")); return }
    if (!image.trim()) { setError(t("create.error_image_missing")); return }
    setBusy(true)
    setError(null)
    try {
      const input: ContainerCreateInput = {
        name,
        description: description.trim() || null,
        image: image.trim(),
        cpu: cpu === "" ? null : Number(cpu),
        ram_mb: ramMb === "" ? null : Number(ramMb),
        network_mode: network,
        node_id: nodeId,
      }
      await containersApi.create(input)
      onCreated()
      onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AdminDialog
      eyebrow="Admin · Container"
      title="Neuer Container"
      icon={<PackagePlus size={16} />}
      onClose={busy ? undefined : onClose}
      maxWidthClass="max-w-xl"
      footer={(
        <>
          <AdminAction onClick={onClose} disabled={busy}>Abbrechen</AdminAction>
          <AdminAction type="submit" form={formId} tone="primary" disabled={busy || !validName}>
            {busy ? t("create.submitting") : t("create.submit")}
          </AdminAction>
        </>
      )}
    >
      <form id={formId} onSubmit={submit} className="space-y-5">
        <AdminField label={t("create.field_name")} help={t("create.field_name_hint")}>
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="searxng" className={adminInputClass} autoFocus />
        </AdminField>
        <AdminField label={t("create.field_desc")}>
          <input value={description} onChange={(event) => setDescription(event.target.value)} className={adminInputClass} />
        </AdminField>

        <AdminField label={t("create.field_image")}>
          {customImage ? (
            <input value={image} onChange={(event) => setImage(event.target.value)}
              placeholder="z.B. images:ubuntu/24.04 oder ubuntu/24.04" className={`${adminInputClass} font-mono`} />
          ) : (
            <div className="grid grid-cols-2 gap-2">
              {quickImages.map((quickImage) => (
                <button key={quickImage} type="button" onClick={() => setImage(quickImage)} aria-pressed={image === quickImage}
                  className={`rounded-[4px] border p-2.5 text-left font-mono text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#69d7ff]/45 ${image === quickImage
                    ? "border-[#69d7ff]/60 bg-[#163248] text-[#c8f2ff]"
                    : "border-[#2a364b] bg-[#111827] text-[#b9c5d6] hover:border-[#46617f]"}`}>
                  {quickImage}
                </button>
              ))}
            </div>
          )}
          <button type="button" onClick={() => setCustomImage((current) => !current)}
            className="mt-1 text-[11px] text-[#69d7ff] hover:text-[#c8f2ff]">
            {customImage ? t("create.back_to_list") : t("create.custom_image_label")}
          </button>
        </AdminField>

        <div className="grid grid-cols-2 gap-3">
          <AdminField label={t("create.field_cpu")} help={t("create.field_cpu_hint")}>
            <input type="number" min={1} max={16} value={cpu}
              onChange={(event) => setCpu(event.target.value === "" ? "" : Math.max(1, Math.min(16, parseInt(event.target.value, 10) || 1)))}
              placeholder="—" className={adminInputClass} />
          </AdminField>
          <AdminField label={t("create.field_ram")} help={t("create.field_ram_hint")}>
            <input type="number" min={64} max={32768} step={64} value={ramMb}
              onChange={(event) => setRamMb(event.target.value === "" ? "" : Math.max(64, Math.min(32768, parseInt(event.target.value, 10) || 64)))}
              placeholder="—" className={adminInputClass} />
          </AdminField>
        </div>

        <AdminField label={t("create.field_network")}>
          <div className="grid grid-cols-2 gap-2">
            <RadioCard active={network === "bridged"} onClick={() => setNetwork("bridged")}
              title={t("create.network_bridged_title")} desc={t("create.network_bridged_desc")} />
            <RadioCard active={network === "isolated"} onClick={() => setNetwork("isolated")}
              title={t("create.network_isolated_title")} desc={t("create.network_isolated_desc")} />
          </div>
        </AdminField>

        <NodeSelector value={nodeId} onChange={setNodeId} requireCapability="incus" disabled={busy} />
        {nodeId !== "local" && <AdminFeedback tone="warning">{t("create.remote_placement_note")}</AdminFeedback>}

        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
      </form>
    </AdminDialog>
  )
}
