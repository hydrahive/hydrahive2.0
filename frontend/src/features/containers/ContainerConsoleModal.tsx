import { TerminalSquare } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui"
import { ModalPortal } from "@/shared/ModalPortal"
import type { Container } from "./types"
import { ConsolePane } from "./ConsolePane"

interface Props {
  container: Container
  onClose: () => void
}

export function ContainerConsoleModal({ container, onClose }: Props) {
  return (
    <ModalPortal>
      <AdminDialog
        eyebrow="Admin · Container"
        title={<span className="font-mono">{container.name} — Console</span>}
        icon={<TerminalSquare size={16} />}
        onClose={onClose}
        maxWidthClass="max-w-5xl"
        className="h-[min(80vh,700px)]"
      >
        <ConsolePane containerId={container.container_id} className="h-full" />
      </AdminDialog>
    </ModalPortal>
  )
}
