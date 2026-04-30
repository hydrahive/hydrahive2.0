import { X } from "lucide-react"
import type { Container } from "./types"
import { ConsolePane } from "./ConsolePane"

interface Props {
  container: Container
  onClose: () => void
}

export function ContainerConsoleModal({ container, onClose }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="w-full max-w-5xl rounded-xl border border-white/[10%] bg-zinc-950 shadow-2xl flex flex-col"
        style={{ height: "min(80vh, 700px)" }}>
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/[8%] flex-shrink-0">
          <p className="text-sm font-mono text-zinc-200 truncate">{container.name} <span className="text-[11px] text-zinc-500">— Console</span></p>
          <button onClick={onClose}
            className="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-white/[5%]">
            <X size={16} />
          </button>
        </div>
        <ConsolePane containerId={container.container_id} className="flex-1" />
      </div>
    </div>
  )
}
