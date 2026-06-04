import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { LoginPage } from "@/features/auth/LoginPage"
import { Layout } from "@/shared/Layout"
import type { ReactElement } from "react"
import { moduleRoutes } from "@/modules/index.generated"

interface ModuleRoute { path: string; element: ReactElement }
const appModuleRoutes = moduleRoutes as ModuleRoute[]
import { DashboardPage } from "@/features/dashboard/DashboardPage"
import { SessionDetailPage } from "@/features/analytics/SessionDetailPage"
import { ChatPage } from "@/features/chat/ChatPage"
import { AgentsPage } from "@/features/agents/AgentsPage"
import { ProjectsPage } from "@/features/projects/ProjectsPage"
import { LlmPage } from "@/features/llm/LlmPage"
import { CatalogPage } from "@/features/llm/CatalogPage"
import { McpPage } from "@/features/mcp/McpPage"
import { SkillsPage } from "@/features/skills/SkillsPage"
import { CredentialsPage } from "@/features/credentials/CredentialsPage"
import { SystemPage } from "@/features/system/SystemPage"
import { SettingsPage } from "@/features/system/SettingsPage"
import { UsersPage } from "@/features/users/UsersPage"
import { ProfilePage } from "@/features/profile/ProfilePage"
import { PluginsPage } from "@/features/plugins/PluginsPage"
import { ExtensionsPage } from "@/features/extensions/ExtensionsPage"
import { ModulesPage } from "@/features/modules/ModulesPage"
import { CommunicationPage } from "@/features/communication/CommunicationPage"
import { TeamchatPage } from "@/features/teamchat/TeamchatPage"
import { VMsPage } from "@/features/vms/VMsPage"
import { ContainersPage } from "@/features/containers/ContainersPage"
import { ContainerDetailPage } from "@/features/containers/ContainerDetailPage"
import { ButlerPage } from "@/features/butler/ButlerPage"
import { BuddyPage } from "@/features/buddy/BuddyPage"
import { BuddySettingsPage } from "@/features/buddy/BuddySettingsPage"
import { DataminingPage } from "@/features/datamining/DataminingPage"
import { MemoryPage } from "@/features/memory/MemoryPage"
import { HelpPage } from "@/features/help/HelpPage"
import { ZahnfeePage } from "@/features/zahnfee/ZahnfeePage"
import { FederationPage } from "@/features/federation/FederationPage"
import { StreamingPage } from "@/features/streaming/StreamingPage"
import { NotFoundPage } from "@/shared/NotFoundPage"
import { getLanding } from "@/features/profile/LandingSwitcher"

function Guard({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AdminGuard({ children }: { children: React.ReactNode }) {
  const role = useAuthStore((s) => s.role)
  if (role !== "admin") return <Navigate to="/" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <Guard>
              <Layout />
            </Guard>
          }
        >
          <Route index element={getLanding() === "dashboard" ? <DashboardPage /> : <BuddyPage />} />
          <Route path="buddy/settings" element={<BuddySettingsPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="analytics/session/:sid" element={<SessionDetailPage />} />
          <Route path="werkstatt" element={<ChatPage />} />
          <Route path="werkstatt/:sid" element={<ChatPage />} />
          <Route path="devchat" element={<Navigate to="/werkstatt" replace />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="communication" element={<CommunicationPage />} />
          <Route path="teamchat" element={<TeamchatPage />} />
          <Route path="vms" element={<VMsPage />} />
          <Route path="containers" element={<ContainersPage />} />
          <Route path="containers/:id" element={<ContainerDetailPage />} />
          <Route path="butler" element={<ButlerPage />} />
          <Route path="federation" element={<FederationPage />} />
          <Route path="streaming" element={<StreamingPage />} />
          <Route path="datamining" element={<DataminingPage />} />
          <Route path="memory" element={<MemoryPage />} />
          <Route path="llm" element={<LlmPage />} />
          <Route path="llm/catalog" element={<CatalogPage />} />
          <Route path="mcp" element={<McpPage />} />
          <Route path="skills" element={<SkillsPage />} />
          <Route path="credentials" element={<CredentialsPage />} />
          <Route path="system" element={<SystemPage />} />
          <Route path="system/settings" element={<AdminGuard><SettingsPage /></AdminGuard>} />
          <Route path="users" element={<AdminGuard><UsersPage /></AdminGuard>} />
          <Route path="plugins" element={<AdminGuard><PluginsPage /></AdminGuard>} />
          <Route path="extensions" element={<AdminGuard><ExtensionsPage /></AdminGuard>} />
          <Route path="modules" element={<AdminGuard><ModulesPage /></AdminGuard>} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="help" element={<HelpPage />} />
          <Route path="zahnfee" element={<AdminGuard><ZahnfeePage /></AdminGuard>} />
          {appModuleRoutes.map((r) => (
            <Route key={r.path} path={r.path} element={r.element} />
          ))}
          <Route path="*" element={<NotFoundPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
