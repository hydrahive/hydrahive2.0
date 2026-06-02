import { useState } from "react"
import type { CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { Copy, X } from "lucide-react"
import { externalInstancesApi } from "./api"
import type { CreateInstanceResult } from "./types"
import { rgbFor } from "@/shared/colors"

interface Props {
  onClose: () => void
  onCreated: () => void
}

function configBlock(r: CreateInstanceResult): string {
  const base = window.location.origin
  return [
    `HH_BASE_URL=${base}`,
    `HH_API_KEY=${r.api_key}`,
    `HH_AGENT_ID=${r.agent_id}`,
    `# HH_VERIFY_SSL=0   (nur einkommentieren für self-signed LAN-Cert; sonst bleibt TLS-Verify an)`,
  ].join("\n")
}

export function NewInstanceDialog({ onClose, onCreated }: Props) {
  const { t } = useTranslation("federation")
  const [name, setName] = useState("")
  const [model, setModel] = useState("claude-opus-4-8")
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CreateInstanceResult | null>(null)
  const [error, setError] = useState("")

  async function handleCreate() {
    if (!name.trim()) return
    setLoading(true)
    setError("")
    try {
      const data = await externalInstancesApi.create(name.trim(), model.trim())
      setResult(data)
      onCreated()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t("new_instance.error"))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="box overflow-hidden w-full max-w-lg p-6" style={{ "--c": rgbFor("/federation") } as CSSProperties}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-zinc-100">{t("new_instance.title")}</h2>
          <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300 transition-colors">
            <X size={16} />
          </button>
        </div>

        {!result ? (
          <div className="space-y-4">
            <div>
              <label className="block text-xs text-zinc-400 mb-1.5">{t("new_instance.name_label")}</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleCreate()}
                placeholder={t("new_instance.name_placeholder")}
                className="w-full rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-xs text-zinc-400 mb-1.5">{t("new_instance.model_label")}</label>
              <input
                type="text"
                value={model}
                onChange={e => setModel(e.target.value)}
                className="w-full rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-violet-500/50 focus:ring-1 focus:ring-violet-500/20"
              />
            </div>
            {error && <p className="text-xs text-red-400">{error}</p>}
            <p className="text-xs text-zinc-500">{t("new_instance.hint")}</p>
            <div className="flex justify-end gap-2 pt-1">
              <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 transition-colors">
                {t("new_instance.cancel")}
              </button>
              <button
                onClick={handleCreate}
                disabled={loading || !name.trim()}
                className="px-4 py-1.5 rounded-lg text-sm bg-violet-600 hover:bg-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
              >
                {loading ? t("new_instance.creating") : t("new_instance.create")}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs text-emerald-300">
              {t("new_instance.success_prefix")} <strong>{result.username}</strong> {t("new_instance.success_suffix")}
            </div>
            <pre className="rounded-lg border border-white/[6%] bg-zinc-800/60 p-3 text-xs font-mono text-zinc-300 whitespace-pre-wrap break-all">{configBlock(result)}</pre>
            <div className="flex justify-end gap-2 pt-1">
              <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 transition-colors">
                {t("new_instance.close")}
              </button>
              <button
                onClick={() => navigator.clipboard.writeText(configBlock(result))}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm bg-violet-600 hover:bg-violet-500 text-white transition-colors"
              >
                <Copy size={13} />
                {t("new_instance.copy")}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
