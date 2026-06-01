import { useState } from "react"
import { useTranslation } from "react-i18next"
import { FileTree } from "./FileTree"
import { useWorkspace } from "./useWorkspace"

type Tab = "files" | "git" | "editor"

export function WorkspacePanel({ agentId }: { agentId: string | null }) {
  const { t } = useTranslation("workspace")
  const [tab, setTab] = useState<Tab>("files")
  const ws = useWorkspace(agentId)

  if (!agentId) return <div className="p-4 text-[11px] text-zinc-600">{t("no_file")}</div>

  return (
    <div className="flex flex-col h-full">
      <div className="px-2.5 py-2 border-b border-white/[6%] text-[11px] font-medium text-zinc-300">{t("title")}</div>
      <div className="flex border-b border-white/[6%] text-[10px]">
        {(["files", "git", "editor"] as Tab[]).map((id) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex-1 py-1.5 ${tab === id ? "text-violet-300 border-b-2 border-violet-500 bg-violet-500/5" : "text-zinc-500"}`}>
            {t(`tab_${id}`)}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-1">
        {tab === "files" && <FileTree agentId={agentId} path="" onOpen={(p) => { ws.open(p); setTab("editor") }} />}
        {tab === "editor" && <div className="p-2 text-[11px] text-zinc-500 font-mono break-all">{ws.openFile?.path ?? t("no_file")}</div>}
        {tab === "git" && <div className="p-2 text-[11px] text-zinc-500">{t("no_repo")}</div>}
      </div>
    </div>
  )
}
