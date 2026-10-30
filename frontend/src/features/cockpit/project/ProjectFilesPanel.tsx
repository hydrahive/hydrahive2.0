import { WorkspacePanel } from "@/features/chat/workspace/WorkspacePanel"
import { CockpitPanel } from "../CockpitPanel"
import type { FileKind } from "@/features/chat/workspace/fileType"

interface Props {
  agentId: string | null
  projectId: string | null
  onOpenFile: (path: string, kind: FileKind) => void
}

export function ProjectFilesPanel({ agentId, projectId, onOpenFile }: Props) {
  return (
    <CockpitPanel theme="werkzeug" title="Dateien & Workspace" eyebrow="Workspace" flush bodyClassName="flex flex-col overflow-hidden">
      <div className="min-h-0 flex-1 overflow-hidden">
        <WorkspacePanel agentId={agentId} projectId={projectId} onOpenFile={onOpenFile} />
      </div>
    </CockpitPanel>
  )
}
