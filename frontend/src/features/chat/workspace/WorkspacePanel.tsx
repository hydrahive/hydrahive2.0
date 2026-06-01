import { useState } from "react"
import { useTranslation } from "react-i18next"
import { FileTree } from "./FileTree"
import { FileEditor } from "./FileEditor"
import { MediaViewer } from "./MediaViewer"
import { useWorkspace } from "./useWorkspace"
import { classifyFile, type FileKind } from "./fileType"

type Tab = "files" | "git" | "editor"

export function WorkspacePanel({ agentId }: { agentId: string | null }) {
  const { t } = useTranslation("workspace")
  const [tab, setTab] = useState<Tab>("files")
  const [openedPath, setOpenedPath] = useState<string | null>(null)
  const [kind, setKind] = useState<FileKind>("text")
  const ws = useWorkspace(agentId)

  if (!agentId) return <div className="p-4 text-[11px] text-zinc-600">{t("no_file")}</div>

  function handleOpen(path: string) {
    const k = classifyFile(path)
    setOpenedPath(path)
    setKind(k)
    if (k === "text") ws.open(path)
    setTab("editor")
  }

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
      <div className="flex-1 min-h-0 overflow-y-auto">
        {tab === "files" && <div className="p-1"><FileTree agentId={agentId} path="" onOpen={handleOpen} /></div>}
        {tab === "editor" && !openedPath && <div className="p-2 text-[11px] text-zinc-500">{t("no_file")}</div>}
        {tab === "editor" && openedPath && kind === "text" && ws.openFile && (
          <FileEditor file={ws.openFile} onSave={ws.save} />
        )}
        {tab === "editor" && openedPath && kind === "text" && !ws.openFile && (
          <div className="p-2 text-[11px] text-zinc-600">{t("loading")}</div>
        )}
        {tab === "editor" && openedPath && kind !== "text" && (
          <MediaViewer agentId={agentId} path={openedPath} kind={kind} />
        )}
        {tab === "git" && <div className="p-2 text-[11px] text-zinc-500">{t("no_repo")}</div>}
      </div>
    </div>
  )
}
