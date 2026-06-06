import { CheckSquare } from "lucide-react"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { useTasks } from "../useTasks"
import type { Task } from "../types"

const PRIORITY_DOT: Record<Task["priority"], string> = {
  high:   "bg-rose-400 shadow-[0_0_4px_rgba(251,113,133,0.6)]",
  medium: "bg-amber-400",
  low:    "bg-zinc-600",
}

interface Props {
  onPrompt: (text: string) => void
}

export function TaskBuddyBox({ onPrompt }: Props) {
  const { tasks, complete } = useTasks({ status: "open", pollMs: 8000 })
  const inProgress = tasks.filter((t) => t.status === "in_progress")
  const open = tasks.filter((t) => t.status === "open")
  const visible = [...inProgress, ...open].slice(0, 6)

  return (
    <CollapsibleBox
      boxId="buddy-tasks"
      icon={<CheckSquare size={14} className="text-violet-400" />}
      title="Aufgaben"
      color="138,92,246"
      defaultCollapsed={false}
      className="w-60"
      headerRight={
        <span className="text-[10px] text-zinc-600">
          {tasks.length > 0 ? `${tasks.length} offen` : "keine"}
        </span>
      }
    >
      <div className="p-2 space-y-1">
        {visible.length === 0 ? (
          <p className="text-[11px] text-zinc-600 px-1 py-0.5">Keine offenen Aufgaben</p>
        ) : (
          visible.map((task) => (
            <div key={task.id} className="flex items-start gap-1.5 group">
              <button
                onClick={() => complete(task.id)}
                className="mt-0.5 flex-shrink-0 w-3.5 h-3.5 rounded border border-white/[8%] hover:border-violet-500/50 hover:bg-violet-500/10 transition-colors"
                title="Als erledigt markieren"
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1">
                  <div className={`flex-shrink-0 w-1.5 h-1.5 rounded-full ${PRIORITY_DOT[task.priority]}`} />
                  <span
                    className="text-[11px] text-zinc-300 truncate cursor-pointer hover:text-zinc-100"
                    onClick={() => onPrompt(`Zeige mir den Status von Task: "${task.title}"`)}
                    title={task.title}
                  >
                    {task.title}
                  </span>
                </div>
                {task.status === "in_progress" && (
                  <span className="text-[9px] text-amber-400 ml-3">in Arbeit</span>
                )}
              </div>
            </div>
          ))
        )}
        {tasks.length > 6 && (
          <p className="text-[10px] text-zinc-600 px-1 pt-1">
            +{tasks.length - 6} weitere →{" "}
            <button
              onClick={() => onPrompt("Zeige mir alle offenen Aufgaben")}
              className="text-violet-400 hover:text-violet-300 underline"
            >
              Alle anzeigen
            </button>
          </p>
        )}
        <button
          onClick={() => onPrompt("Welche Aufgaben sind noch offen? Gib mir eine kurze Übersicht.")}
          className="w-full text-left text-xs px-2 py-1.5 mt-1 rounded-lg border border-white/[6%] hover:border-violet-500/30 hover:bg-violet-500/[3%] text-zinc-400 hover:text-zinc-300 transition-all"
        >
          ✦ Aufgaben besprechen
        </button>
      </div>
    </CollapsibleBox>
  )
}
