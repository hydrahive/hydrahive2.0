import { useEffect, useState } from "react"
import { Loader2, Plus, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { skillsApi } from "./api"
import { SkillEditor } from "./SkillEditor"
import type { Skill } from "./types"

export function SkillsPage() {
  const { t } = useTranslation("skills")
  const role = useAuthStore((s) => s.role)
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [editor, setEditor] = useState<Skill | "new" | null>(null)

  async function reload() {
    setLoading(true)
    try { setSkills(await skillsApi.list({ scope: "all" })) }
    catch { setSkills([]) }
    finally { setLoading(false) }
  }

  useEffect(() => { reload() }, [])

  const userSkills = skills.filter((s) => s.scope === "user")
  const systemSkills = skills.filter((s) => s.scope === "system")

  return (
    <div className="space-y-5 max-w-4xl">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-white">{t("title")}</h1>
          <p className="text-zinc-500 text-sm mt-0.5">{t("subtitle")}</p>
        </div>
        <button onClick={() => setEditor("new")}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs font-medium">
          <Plus size={12} /> {t("new")}
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={20} className="animate-spin text-zinc-500" />
        </div>
      ) : (
        <>
          <Section title={t("section_user")} skills={userSkills} onClick={setEditor}
            emptyHint={t("section_user_empty")} />
          {systemSkills.length > 0 && (
            <Section title={t("section_system")} skills={systemSkills} onClick={setEditor}
              emptyHint={t("section_system_empty")} />
          )}
        </>
      )}

      {editor && (
        <SkillEditor
          skill={editor === "new" ? null : editor}
          defaultScope="user"
          onClose={() => setEditor(null)}
          onSaved={async () => { setEditor(null); await reload() }}
          onDeleted={role === "admin" || (typeof editor !== "string" && editor.scope === "user")
            ? async () => { setEditor(null); await reload() } : undefined}
        />
      )}
    </div>
  )
}

function Section({ title, skills, onClick, emptyHint }: {
  title: string; skills: Skill[]; onClick: (s: Skill) => void; emptyHint: string
}) {
  return (
    <div className="space-y-2">
      <h2 className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500">{title}</h2>
      {skills.length === 0 ? (
        <p className="text-xs text-zinc-600 py-3">{emptyHint}</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {skills.map((s) => (
            <button key={`${s.scope}:${s.name}`} onClick={() => onClick(s)}
              className="text-left rounded-lg border border-white/[8%] bg-white/[2%] p-3 hover:border-white/[15%] hover:bg-white/[5%] transition-colors">
              <div className="flex items-center gap-2 mb-1">
                <Sparkles size={11} className="text-violet-300 flex-shrink-0" />
                <p className="text-sm font-mono text-zinc-200 truncate flex-1">{s.name}</p>
                <span className="text-[10px] text-zinc-600">{s.scope}</span>
              </div>
              {s.description && <p className="text-xs text-zinc-400 line-clamp-2">{s.description}</p>}
              {s.when_to_use && (
                <p className="text-[10px] text-zinc-600 mt-1 line-clamp-1 italic">→ {s.when_to_use}</p>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
