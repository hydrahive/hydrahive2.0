import { Container } from "lucide-react"

export function ContainerGitNotice({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`rounded-[4px] border border-cyan-400/25 bg-cyan-500/[7%] ${compact ? "p-2" : "p-3"}`}>
      <div className="flex items-start gap-2">
        <Container size={compact ? 15 : 17} className="mt-0.5 shrink-0 text-cyan-300" aria-hidden="true" />
        <div>
          <p className="text-xs font-semibold text-cyan-100">Git läuft im Container</p>
          <p className="mt-1 text-[11px] leading-5 text-[#9aa7bc]">
            HydraHive führt hier keine Git-Befehle auf dem Server aus. Status, Commits, Pull und Push erledigst du
            im Container-Terminal oder durch den Projekt-Agenten.
          </p>
        </div>
      </div>
    </div>
  )
}
