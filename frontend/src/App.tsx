import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { LoginPage } from "@/features/auth/LoginPage"
import { Layout } from "@/shared/Layout"
import { DashboardPage } from "@/features/dashboard/DashboardPage"
import { ChatPage } from "@/features/chat/ChatPage"
import { AgentsPage } from "@/features/agents/AgentsPage"
import { ProjectsPage } from "@/features/projects/ProjectsPage"
import { LlmPage } from "@/features/llm/LlmPage"
import { McpPage } from "@/features/mcp/McpPage"
import { SkillsPage } from "@/features/skills/SkillsPage"
import { CredentialsPage } from "@/features/credentials/CredentialsPage"
import { SystemPage } from "@/features/system/SystemPage"
import { UsersPage } from "@/features/users/UsersPage"
import { ProfilePage } from "@/features/profile/ProfilePage"
import { PluginsPage } from "@/features/plugins/PluginsPage"
import { CommunicationPage } from "@/features/communication/CommunicationPage"
import { VMsPage } from "@/features/vms/VMsPage"
import { ContainersPage } from "@/features/containers/ContainersPage"
import { ContainerDetailPage } from "@/features/containers/ContainerDetailPage"
import { ButlerPage } from "@/features/butler/ButlerPage"
import { BuddyPage } from "@/features/buddy/BuddyPage"
import { HelpPage } from "@/features/help/HelpPage"
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
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="devchat" element={<ChatPage />} />
          <Route path="chat" element={<Navigate to="/devchat" replace />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="communication" element={<CommunicationPage />} />
          <Route path="vms" element={<VMsPage />} />
          <Route path="containers" element={<ContainersPage />} />
          <Route path="containers/:id" element={<ContainerDetailPage />} />
          <Route path="butler" element={<ButlerPage />} />
          <Route path="llm" element={<LlmPage />} />
          <Route path="mcp" element={<McpPage />} />
          <Route path="skills" element={<SkillsPage />} />
          <Route path="credentials" element={<CredentialsPage />} />
          <Route path="system" element={<SystemPage />} />
          <Route path="users" element={<AdminGuard><UsersPage /></AdminGuard>} />
          <Route path="plugins" element={<AdminGuard><PluginsPage /></AdminGuard>} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="help" element={<HelpPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
