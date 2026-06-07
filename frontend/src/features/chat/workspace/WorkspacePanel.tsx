import { type ComponentType, Suspense, useState, type CSSProperties } from "react"
import { useTranslation } from "react-i18next"
import { FileTree } from "./FileTree"
import { GitPanel } from "./GitPanel"
import { classifyFile, type FileKind } from "./fileType"
import { rgbFor } from "@/shared/colors"
import { moduleWorkspaceTabs } from "@/modules/index.generated"

interface WorkspaceTabDef {
  id: string
  label: string
  component: ComponentType
}

const extraTabs = moduleWorkspaceTabs as WorkspaceTabDef[]

type CoreTab = "files" | "git"
type Tab = CoreTab | string

interface Props {
  agentId: string | null
  onOpenFile: (path: string, kind: FileKind) => void
}

export function WorkspacePanel({ agentId, onOpenFile }: Props) {
  const { t } = useTranslation("workspace")
  const [tab, setTab] = useState<Tab>("files")

  if (!agentId) return <div className="p-4 text-[11px] text-zinc-600">{t("no_file")}</div>

  const coreTabs: CoreTab[] = ["files", "git"]
  const allTabs = [...coreTabs, ...extraTabs.map((x) => x.id)]

  return (
    <div className="box flex flex-col h-full" style={{ "--c": rgbFor("/werkstatt") } as CSSProperties}>
      <div className="px-2.5 py-2 border-b border-white/[6%] text-[11px] font-medium text-zinc-300">{t("title")}</div>
      <div className="flex border-b border-white/[6%] text-[10px]">
        {allTabs.map((id) => {
          const extra = extraTabs.find((x) => x.id === id)
          const label = extra ? extra.label : t(`tab_${id}`)
          return (
            <button key={id} onClick={() => setTab(id)}
              className={`flex-1 py-1.5 ${tab === id ? "text-violet-300 border-b-2 border-violet-500 bg-violet-500/5" : "text-zinc-500"}`}>
              {label}
            </button>
          )
        })}
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto">
        {tab === "files" && (
          <div className="p-1">
            <FileTree agentId={agentId} path="" onOpen={(p) => onOpenFile(p, classifyFile(p))} />
          </div>
        )}
        {tab === "git" && <GitPanel agentId={agentId} />}
        {extraTabs.map(({ id, component: Comp }) =>
          tab === id ? (
            <Suspense key={id} fallback={<div className="p-4 text-[11px] text-zinc-600">Laden…</div>}>
              <Comp />
            </Suspense>
          ) : null
        )}
      </div>
    </div>
  )
}
