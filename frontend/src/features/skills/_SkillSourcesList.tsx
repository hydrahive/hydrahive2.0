import { Plus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { SkillSource } from "./types"

interface Props {
  sources: SkillSource[]
  onChange: (sources: SkillSource[]) => void
}

export function SkillSourcesList({ sources, onChange }: Props) {
  const { t } = useTranslation("skills")
  return (
    <div className="space-y-1">
      {sources.map((src, i) => (
        <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-1 items-start">
          <div className="space-y-0.5">
            <input value={src.url}
              onChange={(e) => onChange(sources.map((s, j) => j === i ? { ...s, url: e.target.value } : s))}
              placeholder="https://forum.metin2.de/api/threads"
              className="w-full px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 font-mono" />
            <input value={src.description}
              onChange={(e) => onChange(sources.map((s, j) => j === i ? { ...s, description: e.target.value } : s))}
              placeholder={t("source_description_placeholder")}
              className="w-full px-2 py-1 rounded-md bg-zinc-950/50 border border-white/[6%] text-[11px] text-zinc-400" />
          </div>
          <input value={src.auth}
            onChange={(e) => onChange(sources.map((s, j) => j === i ? { ...s, auth: e.target.value } : s))}
            placeholder={t("source_auth_placeholder")}
            title={t("source_auth_hint")}
            className="w-32 px-2 py-1 rounded-md bg-zinc-950 border border-white/[8%] text-xs text-zinc-200 font-mono self-start" />
          <button type="button"
            onClick={() => onChange(sources.filter((_, j) => j !== i))}
            className="p-1.5 rounded text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 self-start">
            <Trash2 size={11} />
          </button>
        </div>
      ))}
      <button type="button"
        onClick={() => onChange([...sources, { url: "", auth: "", description: "" }])}
        className="flex items-center gap-1 px-2 py-1 rounded-md text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-white/5 border border-white/[8%] border-dashed">
        <Plus size={11} /> {t("source_add")}
      </button>
    </div>
  )
}
