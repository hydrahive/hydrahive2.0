import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { LoginPage } from "@/features/auth/LoginPage"
import { Layout } from "@/shared/Layout"
import { DashboardPage } from "@/features/dashboard/DashboardPage"
import { ChatPage } from "@/features/chat/ChatPage"
import { AgentsPage } from "@/features/agents/AgentsPage"
import { ProjectsPage } from "@/features/agents/ProjectsPage"
import { LlmPage } from "@/features/llm/LlmPage"
import { SystemPage } from "@/features/system/SystemPage"

function Guard({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  if (!token) return <Navigate to="/login" replace />
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
          <Route path="llm" element={<LlmPage />} />
          <Route path="system" element={<SystemPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
