import { useTranslation } from "react-i18next"
import { Pickaxe, Search, History, Layers, Cpu } from "lucide-react"

const COMING: { icon: typeof Search; labelKey: string }[] = [
  { icon: Search,   labelKey: "feature_search" },
  { icon: History,  labelKey: "feature_sessions" },
  { icon: Layers,   labelKey: "feature_semantic" },
  { icon: Cpu,      labelKey: "feature_stats" },
]

export function DataminingPage() {
  const { t } = useTranslation("datamining")

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-center gap-3">
        <Pickaxe className="text-amber-400" size={20} />
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
          <p className="text-xs text-zinc-500 mt-0.5">{t("subtitle")}</p>
        </div>
      </div>

      <div className="rounded-xl bg-white/[3%] border border-white/[6%] p-6 space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shrink-0">
            <Pickaxe className="text-white" size={22} />
          </div>
          <div>
            <p className="text-zinc-100 font-medium">{t("coming_soon")}</p>
            <p className="text-xs text-zinc-500 mt-0.5">{t("mcp_hint")}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2">
          {COMING.map(({ icon: Icon, labelKey }) => (
            <div
              key={labelKey}
              className="flex items-center gap-3 rounded-lg bg-white/[3%] border border-white/[5%] px-4 py-3"
            >
              <Icon size={15} className="text-amber-400 shrink-0" />
              <span className="text-xs text-zinc-400">{t(labelKey)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
