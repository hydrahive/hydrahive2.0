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
    <CockpitPanel title="Dateien & Workspace" eyebrow="Workspace" className="min-h-0 flex flex-col overflow-hidden p-0">
      <div className="min-h-0 flex-1 overflow-hidden">
        <WorkspacePanel agentId={agentId} projectId={projectId} onOpenFile={onOpenFile} />
      </div>
    </CockpitPanel>
  )
}
