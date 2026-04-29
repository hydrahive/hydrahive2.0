import { useEffect, useState } from "react"
import { Loader2, Sparkles, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { mcpApi, type QuickAddTemplate } from "./api"

interface Props {
  existingIds: Set<string>
  onCreated: (id: string) => void
}

export function QuickAddPanel({ existingIds, onCreated }: Props) {
  const { t } = useTranslation("mcp")
  const [templates, setTemplates] = useState<QuickAddTemplate[]>([])
  const [active, setActive] = useState<QuickAddTemplate | null>(null)

  useEffect(() => {
    mcpApi.quickAddTemplates().then(setTemplates).catch(() => {})
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Sparkles size={14} className="text-violet-300" />
        <h2 className="text-sm font-semibold text-zinc-300">
          {t("quick_add.title")}
        </h2>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {templates.map((t) => {
          const installed = existingIds.has(t.id)
          return (
            <button
              key={t.id}
              type="button"
              disabled={installed}
              onClick={() => setActive(t)}
              className={`text-left p-4 rounded-xl border transition-all ${
                installed
                  ? "border-emerald-500/20 bg-emerald-500/[5%] cursor-default"
                  : "border-white/[8%] bg-white/[2%] hover:bg-white/[5%] hover:border-violet-500/30 cursor-pointer"
              }`}
            >
              <p className={`text-sm font-medium ${installed ? "text-emerald-300" : "text-zinc-200"}`}>
                {t.name} {installed && "✓"}
              </p>
              <p className="text-xs text-zinc-500 mt-1 leading-snug">{t.description}</p>
              <p className="text-[10.5px] text-zinc-600 mt-2 font-mono truncate">
                {t.command} {t.args.slice(0, 2).join(" ")}
                {t.args.length > 2 && " …"}
              </p>
            </button>
          )
        })}
      </div>

      {active && (
        <QuickAddForm
          template={active}
          onClose={() => setActive(null)}
          onCreated={(id) => { setActive(null); onCreated(id) }}
        />
      )}
    </div>
  )
}

function QuickAddForm({ template, onClose, onCreated }: {
  template: QuickAddTemplate; onClose: () => void; onCreated: (id: string) => void
}) {
  const { t } = useTranslation("mcp")
  const { t: tCommon } = useTranslation("common")
  const [serverId, setServerId] = useState(template.id)
  const [inputs, setInputs] = useState<Record<string, string>>(
    Object.fromEntries(template.user_inputs.map((i) => [i.key, i.default])),
  )
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true); setError(null)
    try {
      const created = await mcpApi.quickAdd(template.id, serverId, inputs)
      onCreated(created.id)
    } catch (e) { setError(e instanceof Error ? e.message : tCommon("status.error")) }
    finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <form onSubmit={submit} onClick={(e) => e.stopPropagation()}
        className="w-full max-w-md rounded-2xl border border-white/[8%] bg-zinc-900 p-6 shadow-2xl shadow-black/40 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">{t("quick_add.form_title", { name: template.name })}</h2>
          <button type="button" onClick={onClose} className="p-1 rounded text-zinc-500 hover:text-zinc-200 hover:bg-white/5">
            <X size={16} />
          </button>
        </div>
        <p className="text-sm text-zinc-500 leading-snug">{template.description}</p>

        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-zinc-400">{t("quick_add.server_id")}</label>
          <input value={serverId} onChange={(e) => setServerId(e.target.value)} required pattern="[a-zA-Z0-9_\-]+"
            className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm font-mono" />
        </div>

        {template.user_inputs.map((field) => (
          <div key={field.key} className="space-y-1.5">
            <label className="block text-xs font-medium text-zinc-400">
              {field.label} {field.required && <span className="text-rose-400">*</span>}
            </label>
            <input
              type={field.secret ? "password" : "text"}
              value={inputs[field.key] ?? ""}
              onChange={(e) => setInputs({ ...inputs, [field.key]: e.target.value })}
              required={field.required}
              className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-white/[8%] text-zinc-200 text-sm font-mono"
            />
          </div>
        ))}

        {error && (
          <p className="text-sm text-rose-300 bg-rose-500/[6%] border border-rose-500/20 rounded-lg px-3 py-2">{error}</p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-4 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 hover:bg-white/5">{tCommon("actions.cancel")}</button>
          <button type="submit" disabled={busy}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-sm font-medium disabled:opacity-40 shadow-md shadow-violet-900/20">
            {busy && <Loader2 size={13} className="animate-spin" />}
            {tCommon("actions.create")}
          </button>
        </div>
      </form>
    </div>
  )
}
