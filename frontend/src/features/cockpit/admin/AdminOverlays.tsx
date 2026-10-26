import { UsersOverlay } from "./UsersOverlay"
import { ModulesOverlay } from "./ModulesOverlay"
import { PluginsOverlay } from "./PluginsOverlay"
import { CredentialsOverlay } from "./CredentialsOverlay"
import { ThemesOverlay } from "./ThemesOverlay"
import { McpOverlay } from "./McpOverlay"
import { LlmOverlay } from "./LlmOverlay"
import { ExtensionsOverlay } from "./ExtensionsOverlay"
import { SystemOverlay } from "./SystemOverlay"
import { SystemSettingsOverlay } from "./SystemSettingsOverlay"
import { ContainersOverlay } from "./ContainersOverlay"
import { VMsOverlay } from "./VMsOverlay"
import { NodesOverlay } from "./NodesOverlay"
import { JobsOverlay } from "./JobsOverlay"
import { ScheduledTasksOverlay } from "./ScheduledTasksOverlay"
import { GrantsOverlay } from "@/features/access/GrantsOverlay"
import { ArchiveOverlay } from "@/features/archive/ArchiveOverlay"
import { FederationOverlay } from "./FederationOverlay"
import type { AdminOverlayId } from "./adminOverlayRegistry"

interface Props {
  overlay: AdminOverlayId | null
  selectedContainerId: string | null
  onClose: () => void
  onSelectContainer: (containerId: string | null) => void
}

/** Rendert das aktive Admin-Fenster (/admin?section=…). */
export function AdminOverlays({ overlay, selectedContainerId, onClose, onSelectContainer }: Props) {
  return (
    <>
      {overlay === "users" && <UsersOverlay onClose={onClose} />}
      {overlay === "modules" && <ModulesOverlay onClose={onClose} />}
      {overlay === "plugins" && <PluginsOverlay onClose={onClose} />}
      {overlay === "credentials" && <CredentialsOverlay onClose={onClose} />}
      {overlay === "themes" && <ThemesOverlay onClose={onClose} />}
      {overlay === "mcp" && <McpOverlay onClose={onClose} />}
      {overlay === "llm" && <LlmOverlay onClose={onClose} />}
      {overlay === "extensions" && <ExtensionsOverlay onClose={onClose} />}
      {overlay === "system" && <SystemOverlay onClose={onClose} />}
      {overlay === "system-settings" && <SystemSettingsOverlay onClose={onClose} />}
      {overlay === "containers" && (
        <ContainersOverlay
          onClose={onClose}
          selectedContainerId={selectedContainerId}
          onSelectContainer={onSelectContainer}
        />
      )}
      {overlay === "vms" && <VMsOverlay onClose={onClose} />}
      {overlay === "nodes" && <NodesOverlay onClose={onClose} />}
      {overlay === "jobs" && <JobsOverlay onClose={onClose} />}
      {overlay === "scheduled-tasks" && <ScheduledTasksOverlay onClose={onClose} />}
      {overlay === "access" && <GrantsOverlay onClose={onClose} />}
      {overlay === "archive" && <ArchiveOverlay onClose={onClose} />}
      {overlay === "federation" && <FederationOverlay onClose={onClose} />}
    </>
  )
}
