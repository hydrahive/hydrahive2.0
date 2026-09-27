import { useCallback, useEffect, useState } from "react"
import { Loader2, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Project } from "@/features/projects/types"
import { skillsApi } from "@/features/skills/api"
import { SkillEditor } from "@/features/skills/SkillEditor"
import type { Skill } from "@/features/skills/types"
import { CockpitButton } from "../CockpitButton"
import { CockpitSectionLabel } from "../CockpitPanel"

/** Geteilte Projekt-Skill-Bibliothek: ansehen, anlegen, bearbeiten (Rechte prüft das Backend). */
export function ProjectSkillsOverlay({ project, onClose }: { project: Project; onClose: () => void }) {
  const { t } = useTranslation("skills")
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editor, setEditor] = useState<Skill | "new" | null>(null)

  const reload = useCallback(async () => {
    try {
      const list = await skillsApi.listProject(project.id)
      setSkills(list)
      setError(null)
    } catch {
      setSkills([])
      setError(t("project_load_error"))
    } finally {
      setLoading(false)
    }
  }, [project.id, t])

  // Laden beim Öffnen; setState passiert erst nach dem await (gleiches Muster wie ThemesOverlay).
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void reload() }, [reload])

  return (
    <div className="fixed inset-0 z-[100] grid place-items-center bg-black/80 p-4" role="dialog" aria-modal="true" aria-labelledby="project-skills-title">
      <section className="flex h-[min(720px,94dvh)] w-full max-w-3xl flex-col overflow-hidden rounded-[6px] border border-[#46617f] bg-[#151c2b] shadow-2xl">
        <header className="flex items-start justify-between gap-3 border-b border-[#2a364b] p-4">
          <div>
            <CockpitSectionLabel>{project.name}</CockpitSectionLabel>
            <h2 id="project-skills-title" className="mt-1 text-lg font-semibold text-[#e8eef8]">{t("project_title")}</h2>
            <p className="mt-1 text-xs text-[#8d9ab0]">{t("project_subtitle")}</p>
          </div>
          <div className="flex shrink-0 gap-2">
            <CockpitButton tone="primary" onClick={() => setEditor("new")}>+ {t("new")}</CockpitButton>
            <CockpitButton onClick={onClose}>Schließen</CockpitButton>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto p-4">
          {loading ? (
            <p className="flex items-center gap-2 text-sm text-[#8d9ab0]"><Loader2 size={14} className="animate-spin" /></p>
          ) : error ? (
            <p className="rounded-[4px] border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</p>
          ) : skills.length === 0 ? (
            <p className="text-sm text-[#8d9ab0]">{t("project_empty")}</p>
          ) : (
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {skills.map((skill) => (
                <button key={skill.name} type="button" onClick={() => setEditor(skill)}
                  className="rounded-[4px] border border-[#2a364b] bg-[#101724] p-3 text-left hover:border-[#69d7ff]/45">
                  <p className="flex items-center gap-2 font-mono text-sm text-[#e8eef8]"><Sparkles size={11} className="text-[#69d7ff]" />{skill.name}</p>
                  {skill.description ? <p className="mt-1 line-clamp-2 text-xs text-[#8d9ab0]">{skill.description}</p> : null}
                  {skill.when_to_use ? <p className="mt-1 line-clamp-1 text-[10px] italic text-[#6d7a90]">→ {skill.when_to_use}</p> : null}
                </button>
              ))}
            </div>
          )}
        </main>
      </section>
      {editor && (
        <SkillEditor
          skill={editor === "new" ? null : editor}
          defaultScope="project"
          ownerForSave={project.id}
          onClose={() => setEditor(null)}
          onSaved={async () => { setEditor(null); await reload() }}
          onDeleted={async () => { setEditor(null); await reload() }}
        />
      )}
    </div>
  )
}
