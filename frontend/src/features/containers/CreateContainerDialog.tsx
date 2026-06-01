import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { X } from "lucide-react"
import type { ContainerCreateInput, NetworkMode } from "./types"
import { containersApi } from "./api"
import { Field, RadioCard } from "./_containerDialogHelpers"

interface Props {
  onClose: () => void
  onCreated: () => void
}

export function CreateContainerDialog({ onClose, onCreated }: Props) {
  const { t } = useTranslation("containers")
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [image, setImage] = useState("debian/12")
  const [customImage, setCustomImage] = useState(false)
  const [cpu, setCpu] = useState<number | "">("")
  const [ramMb, setRamMb] = useState<number | "">("")
  const [network, setNetwork] = useState<NetworkMode>("bridged")
  const [quickImages, setQuickImages] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    containersApi.quickImages().then(setQuickImages).catch(() => setQuickImages([]))
  }, [])

  const validName = /^[a-zA-Z][a-zA-Z0-9-]{0,62}$/.test(name)

  async function submit() {
    if (!validName) { setError(t("create.error_name_invalid")); return }
    if (!image.trim()) { setError(t("create.error_image_missing")); return }
    setBusy(true); setError(null)
    try {
      const input: ContainerCreateInput = {
        name,
        description: description.trim() || null,
        image: image.trim(),
        cpu: cpu === "" ? null : Number(cpu),
        ram_mb: ramMb === "" ? null : Number(ramMb),
        network_mode: network,
      }
      await containersApi.create(input)
      onCreated()
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm flex items-center justify-center" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="w-full max-w-xl mx-4 rounded-2xl border border-white/[8%] bg-zinc-900 shadow-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[6%]">
          <h2 className="text-lg font-bold text-white">Neuer Container</h2>
          <button onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5"><X size={16} /></button>
        </div>
        <div className="overflow-y-auto px-5 py-4 space-y-5">
          <Field label={t("create.field_name")} hint={t("create.field_name_hint")}>
            <input value={name} onChange={(e) => setName(e.target.value)}
              placeholder="searxng"
              className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none" />
          </Field>
          <Field label={t("create.field_desc")}>
            <input value={description} onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none" />
          </Field>

          <Field label={t("create.field_image")}>
            {customImage ? (
              <input value={image} onChange={(e) => setImage(e.target.value)}
                placeholder="z.B. images:ubuntu/24.04 oder ubuntu/24.04"
                className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none" />
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {quickImages.map((q) => (
                  <button key={q} type="button" onClick={() => setImage(q)}
                    className={`text-left p-2.5 rounded-lg border text-xs font-mono transition-colors ${image === q
                      ? "bg-violet-500/15 border-violet-500/40 text-violet-200"
                      : "bg-white/[2%] border-white/[8%] hover:border-white/[15%] text-zinc-300"}`}>
                    {q}
                  </button>
                ))}
              </div>
            )}
            <button type="button" onClick={() => setCustomImage(!customImage)}
              className="mt-1 text-[11px] text-zinc-500 hover:text-zinc-300">
              {customImage ? t("create.back_to_list") : t("create.custom_image_label")}
            </button>
          </Field>

          <div className="grid grid-cols-2 gap-3">
            <Field label={t("create.field_cpu")} hint={t("create.field_cpu_hint")}>
              <input type="number" min={1} max={16} value={cpu}
                onChange={(e) => setCpu(e.target.value === "" ? "" : Math.max(1, Math.min(16, parseInt(e.target.value, 10) || 1)))}
                placeholder="—"
                className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none" />
            </Field>
            <Field label={t("create.field_ram")} hint={t("create.field_ram_hint")}>
              <input type="number" min={64} max={32768} step={64} value={ramMb}
                onChange={(e) => setRamMb(e.target.value === "" ? "" : Math.max(64, Math.min(32768, parseInt(e.target.value, 10) || 64)))}
                placeholder="—"
                className="w-full bg-zinc-950 border border-white/[10%] rounded-lg px-3 py-2 text-sm text-zinc-200 focus:border-violet-500/50 outline-none" />
            </Field>
          </div>

          <Field label={t("create.field_network")}>
            <div className="grid grid-cols-2 gap-2">
              <RadioCard active={network === "bridged"} onClick={() => setNetwork("bridged")}
                title={t("create.network_bridged_title")} desc={t("create.network_bridged_desc")} />
              <RadioCard active={network === "isolated"} onClick={() => setNetwork("isolated")}
                title={t("create.network_isolated_title")} desc={t("create.network_isolated_desc")} />
            </div>
          </Field>

          {error && <div className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/20 rounded-md px-3 py-2">{error}</div>}
        </div>
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-white/[6%]">
          <button onClick={onClose} disabled={busy}
            className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">
            Abbrechen
          </button>
          <button onClick={submit} disabled={busy || !validName}
            className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40">
            {busy ? t("create.submitting") : t("create.submit")}
          </button>
        </div>
      </div>
    </div>
  )
}

