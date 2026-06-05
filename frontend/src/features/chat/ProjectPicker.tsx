import { useTranslation } from "react-i18next"
import type { ProjectBrief } from "./api"

interface Props {
  /** Aktives Projekt der Session, oder null. */
  current: string | null
  projects: ProjectBrief[]
  /** Wird mit der neuen project_id gerufen. null = kein Projekt (Agent-Workspace). */
  onPick: (projectId: string | null) => Promise<void> | void
  busy?: boolean
}

const NONE_VALUE = "__NONE__"

/** Native <select> für die Projektwahl im Chat-Header. Setzt das aktive Projekt
 *  der Session → Runner weist dem Run das Projekt-Workspace zu (cwd = Repo). */
export function ProjectPicker({ current, projects, onPick, busy }: Props) {
  const { t } = useTranslation("chat")
  async function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const value = e.target.value
    await onPick(value === NONE_VALUE ? null : value)
  }

  return (
    <select
      value={current ?? NONE_VALUE}
      onChange={handleChange}
      disabled={busy}
      title={t("project_picker_title")}
      className="appearance-none cursor-pointer px-2 py-0.5 pr-6 rounded text-xs max-w-[10rem] truncate transition-colors
        bg-no-repeat bg-[length:10px] bg-[position:right_4px_center]
        bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 24 24%22 fill=%22none%22 stroke=%22%2334d399%22 stroke-width=%222%22 stroke-linecap=%22round%22 stroke-linejoin=%22round%22><polyline points=%226 9 12 15 18 9%22/></svg>')]
        bg-emerald-500/15 text-emerald-200 border border-emerald-500/30 hover:bg-emerald-500/20 disabled:opacity-40"
    >
      <option value={NONE_VALUE} className="bg-zinc-900 text-zinc-300">⬡ Kein Projekt</option>
      {projects.map((p) => (
        <option key={p.id} value={p.id} className="bg-zinc-900 text-zinc-300">{p.name}</option>
      ))}
    </select>
  )
}
