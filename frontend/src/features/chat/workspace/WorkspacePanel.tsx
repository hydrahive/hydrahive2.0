import { type ComponentType, Suspense, useState } from "react"
import { useTranslation } from "react-i18next"
import { RefreshCw } from "lucide-react"
import { useRunFinished } from "@/shared/runFinished"
import { FileTree } from "./FileTree"
import { GitPanel } from "./GitPanel"
import { classifyFile, type FileKind } from "./fileType"
import { moduleWorkspaceTabs } from "@/modules/index.generated"

interface WorkspaceTabDef {
  id: string
  label: string
  component: ComponentType<{ projectId?: string | null }>
}

const extraTabs = moduleWorkspaceTabs as WorkspaceTabDef[]

type CoreTab = "files" | "git"
type Tab = CoreTab | string

interface Props {
  agentId: string | null
  projectId?: string | null
  onOpenFile: (path: string, kind: FileKind) => void
}

export function WorkspacePanel({ agentId, projectId, onOpenFile }: Props) {
  const { t } = useTranslation("workspace")
  const [tab, setTab] = useState<Tab>("files")
  // Neuer key = FileTree lädt neu (nach Agent-Lauf oder per Knopf).
  const [treeRevision, setTreeRevision] = useState(0)
  useRunFinished(() => setTreeRevision((n) => n + 1))

  if (!agentId) return <div className="p-4 text-[11px] text-zinc-600">{t("no_file")}</div>

  const coreTabs: CoreTab[] = ["files", "git"]
  const allTabs = [...coreTabs, ...extraTabs.map((x) => x.id)]

  return (
    <div className="flex h-full flex-col overflow-hidden bg-[#151c2b] text-[#e8eef8]">
      <div className="flex items-center justify-between border-b border-[#2a364b] bg-[#121a29] px-3 py-2 text-[11px] font-black uppercase tracking-[0.12em] text-[#69d7ff]">
        {t("title")}
        <button type="button" onClick={() => setTreeRevision((n) => n + 1)} title={t("refresh")} aria-label={t("refresh")}
          className="rounded-[4px] p-1 text-[#8d9ab0] hover:bg-[#172133] hover:text-[#e8eef8]">
          <RefreshCw size={12} />
        </button>
      </div>
      <div className="flex border-b border-[#2a364b] bg-[#111827] text-[10px]">
        {allTabs.map((id) => {
          const extra = extraTabs.find((x) => x.id === id)
          const label = extra ? extra.label : t(`tab_${id}`)
          return (
            <button key={id} onClick={() => setTab(id)}
              className={`flex-1 border-b-2 py-1.5 font-semibold transition-colors ${tab === id ? "border-[#69d7ff] bg-[#1c2940] text-[#69d7ff]" : "border-transparent text-[#8d9ab0] hover:bg-[#172133] hover:text-[#e8eef8]"}`}>
              {label}
            </button>
          )
        })}
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto">
        {tab === "files" && (
          <div className="p-1">
            <FileTree key={`files-${treeRevision}`} agentId={agentId} path="" onOpen={(p) => onOpenFile(p, classifyFile(p))} />
          </div>
        )}
        {tab === "git" && <GitPanel agentId={agentId} />}
        {extraTabs.map(({ id, component: Comp }) =>
          tab === id ? (
            <Suspense key={id} fallback={<div className="p-4 text-[11px] text-zinc-600">Laden…</div>}>
              <Comp projectId={projectId} />
            </Suspense>
          ) : null
        )}
      </div>
    </div>
  )
}
