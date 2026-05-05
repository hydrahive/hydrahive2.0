import { CheckCircle, Pencil, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { LlmProvider } from "./api"

export function ProviderCard({
  provider,
  onEdit,
  onDelete,
}: {
  provider: LlmProvider
  onEdit: () => void
  onDelete: () => void
}) {
  const { t } = useTranslation("llm")
  const hasOAuth = !!provider.oauth?.access
  return (
    <div className="flex items-center gap-3 p-4 rounded-xl border border-white/[8%] bg-white/[3%]">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-200">{provider.name || provider.id}</p>
        <p className="text-xs text-zinc-500 mt-0.5 flex items-center gap-1.5">
          {hasOAuth ? (
            <span className="flex items-center gap-1 text-emerald-400">
              <CheckCircle size={11} /> OAuth
              {provider.oauth?.account_id && (
                <span className="text-zinc-500 font-mono">· {provider.oauth.account_id.slice(0, 12)}…</span>
              )}
            </span>
          ) : provider.api_key ? (
            <span>{"••••••••" + provider.api_key.slice(-4)}</span>
          ) : (
            <span>{t("providers.no_key")}</span>
          )}
          <span>·</span>
          <span>{t("providers.models_count", { count: provider.models.length })}</span>
        </p>
      </div>
      <button onClick={onEdit}
        className="p-1.5 rounded-lg text-zinc-600 hover:text-violet-300 hover:bg-violet-500/10 transition-colors">
        <Pencil size={14} />
      </button>
      <button onClick={onDelete}
        className="p-1.5 rounded-lg text-zinc-600 hover:text-rose-400 hover:bg-rose-500/10 transition-colors">
        <Trash2 size={14} />
      </button>
    </div>
  )
}
