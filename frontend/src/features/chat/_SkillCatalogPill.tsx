import { useEffect, useRef, useState } from "react"
import { BookOpen, X } from "lucide-react"
import { skillsApi } from "@/features/skills/api"
import type { Skill } from "@/features/skills/types"

interface Props {
  agentId: string | null
  insert: (text: string) => void
}

export function SkillCatalogPill({ agentId, insert }: Props) {
  const [open, setOpen] = useState(false)
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    skillsApi
      .list(agentId ? { agentId } : { scope: "all" })
      .then(setSkills)
      .catch(() => setSkills([]))
      .finally(() => setLoading(false))
  }, [open, agentId])

  useEffect(() => {
    function onOutsideClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener("mousedown", onOutsideClick)
    return () => document.removeEventListener("mousedown", onOutsideClick)
  }, [open])

  function handleSelect(skill: Skill) {
    insert(`Nutze den Skill "${skill.name}": `)
    setOpen(false)
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        title="Skill-Katalog"
        onClick={() => setOpen((v) => !v)}
        className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full border text-[10px] font-medium transition-colors
          ${open
            ? "text-violet-300 bg-violet-500/20 border-violet-500/40"
            : "text-violet-300 bg-violet-500/10 hover:bg-violet-500/20 border-violet-500/30"
          }`}
      >
        <BookOpen size={11} />
        <span>skills</span>
      </button>

      {open && (
        <div className="absolute bottom-full mb-2 right-0 z-50 w-72 rounded-xl border border-white/[8%] bg-zinc-900/98 shadow-2xl backdrop-blur-sm">
          <div className="flex items-center justify-between px-3 pt-3 pb-2 border-b border-white/[6%]">
            <span className="text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">Skill-Katalog</span>
            <button onClick={() => setOpen(false)} className="text-zinc-600 hover:text-zinc-400 transition-colors">
              <X size={12} />
            </button>
          </div>

          <div className="p-3 max-h-56 overflow-y-auto">
            {loading ? (
              <p className="text-xs text-zinc-600 text-center py-4">Lade…</p>
            ) : skills.length === 0 ? (
              <p className="text-xs text-zinc-600 text-center py-4">Keine Skills verfügbar</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {skills.map((s) => (
                  <button
                    key={s.name}
                    title={s.description || s.when_to_use || s.name}
                    onClick={() => handleSelect(s)}
                    className="px-2 py-1 rounded-lg bg-white/[3%] border border-white/[6%] text-zinc-300 text-[11px] font-mono
                      hover:bg-violet-500/10 hover:border-violet-500/30 hover:text-violet-300 transition-colors"
                  >
                    {s.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="px-3 pb-2 text-[9px] text-zinc-600 border-t border-white/[6%] pt-2">
            Klick fügt Skill als Anweisung in die Eingabe ein
          </div>
        </div>
      )}
    </div>
  )
}
