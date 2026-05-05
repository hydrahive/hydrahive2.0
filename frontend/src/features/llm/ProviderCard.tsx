import { Pencil, Trash2 } from "lucide-react"
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
  return (
    <div className="flex items-center gap-3 p-4 rounded-xl border border-white/[8%] bg-white/[3%]">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-zinc-200">{provider.name || provider.id}</p>
        <p className="text-xs text-zinc-500 mt-0.5">
          {provider.api_key ? "••••••••" + provider.api_key.slice(-4) : t("providers.no_key")}
          {" · "}
          {t("providers.models_count", { count: provider.models.length })}
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
