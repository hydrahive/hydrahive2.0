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
import { SystemPage } from "@/features/system/SystemPage"
import { UsersPage } from "@/features/users/UsersPage"
import { ProfilePage } from "@/features/profile/ProfilePage"
import { PluginsPage } from "@/features/plugins/PluginsPage"
import { CommunicationPage } from "@/features/communication/CommunicationPage"
import { VMsPage } from "@/features/vms/VMsPage"
import { ContainersPage } from "@/features/containers/ContainersPage"

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
          <Route index element={<DashboardPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="communication" element={<CommunicationPage />} />
          <Route path="vms" element={<VMsPage />} />
          <Route path="containers" element={<ContainersPage />} />
          <Route path="llm" element={<LlmPage />} />
          <Route path="mcp" element={<McpPage />} />
          <Route path="system" element={<SystemPage />} />
          <Route path="users" element={<AdminGuard><UsersPage /></AdminGuard>} />
          <Route path="plugins" element={<AdminGuard><PluginsPage /></AdminGuard>} />
          <Route path="profile" element={<ProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
