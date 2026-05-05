import { Pencil, Trash2, KeyRound } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { LlmProvider } from "./api"

function formatExpiry(unixSec: number): string {
  const ms = unixSec * 1000
  const diff = ms - Date.now()
  if (diff < 0) return "abgelaufen"
  const min = Math.round(diff / 60000)
  if (min < 60) return `${min} min`
  const h = Math.round(min / 60)
  if (h < 48) return `${h} h`
  return `${Math.round(h / 24)} d`
}

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
        <p className="text-sm font-medium text-zinc-200 flex items-center gap-2">
          {provider.name || provider.id}
          {hasOAuth && (
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-violet-500/15 text-violet-300 border border-violet-500/30">
              <KeyRound size={10} /> OAuth
            </span>
          )}
        </p>
        <p className="text-xs text-zinc-500 mt-0.5">
          {hasOAuth
            ? `OAuth · läuft ab in ${formatExpiry(provider.oauth?.expires_at ?? 0)}`
            : provider.api_key
              ? "••••••••" + provider.api_key.slice(-4)
              : t("providers.no_key")}
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
