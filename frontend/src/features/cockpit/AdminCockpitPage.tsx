import { useState, type ComponentType } from "react"
import { Boxes, Brain, CircuitBoard, Container, DatabaseBackup, GitBranch, KeyRound, MonitorCog, PlugZap, Server, ShieldAlert, SlidersHorizontal, Users, WandSparkles } from "lucide-react"
import { CockpitButton } from "./CockpitButton"
import { CockpitPanel, CockpitSectionLabel } from "./CockpitPanel"
import { CockpitShell } from "./CockpitShell"
import { CockpitTopbar } from "./CockpitTopbar"
import { adminOfflineActions, explicitAiActions, openLocalPath } from "./actionRegistry"
import { UsersOverlay } from "./admin/UsersOverlay"
import { ModulesOverlay } from "./admin/ModulesOverlay"
import { PluginsOverlay } from "./admin/PluginsOverlay"
import { CredentialsOverlay } from "./admin/CredentialsOverlay"
import { ThemesOverlay } from "./admin/ThemesOverlay"
import { McpOverlay } from "./admin/McpOverlay"
import { LlmOverlay } from "./admin/LlmOverlay"

/** Admin-Bereiche, die bereits als eingerastetes Cockpit-Overlay existieren.
 *  Alles andere fällt (noch) auf die bestehende Legacy-Seite via openLocalPath. */
type AdminOverlayId = "users" | "modules" | "plugins" | "credentials" | "themes" | "mcp" | "llm"

const adminIcons = [Server, Users, Boxes, PlugZap, CircuitBoard, KeyRound]
// action.ids mit Overlay werden eingerastet, der Rest per Pfad geöffnet.
const adminLinks = adminOfflineActions.map((action, index) => ({ id: action.id, title: action.label, path: action.path ?? "/admin", icon: adminIcons[index] ?? Server, desc: action.description ?? "Lokale Admin-Seite öffnen." }))
const OVERLAY_BY_ACTION: Record<string, AdminOverlayId> = { users: "users", modules: "modules", plugins: "plugins", credentials: "credentials" }
// Pfad-basierte Kacheln (Ops/Integrationen ohne action.id) auf Overlays mappen.
const OVERLAY_BY_PATH: Record<string, AdminOverlayId> = { "/modules": "modules", "/plugins": "plugins", "/credentials": "credentials", "/themes": "themes", "/mcp": "mcp", "/llm": "llm" }

const opsLinks = [
  { title: "LLM", path: "/llm", icon: Brain },
  { title: "MCP", path: "/mcp", icon: WandSparkles },
  { title: "Skills", path: "/skills", icon: SlidersHorizontal },
  { title: "VMs", path: "/vms", icon: MonitorCog },
  { title: "Container", path: "/containers", icon: Container },
  { title: "Themes", path: "/themes", icon: WandSparkles },
]

const integrationLinks = [
  { title: "Gitea", path: "/extensions", icon: GitBranch, text: "Lokaler Git-Server, Repo-Spiegel und Projekt-Remotes." },
  { title: "Credentials", path: "/credentials", icon: KeyRound, text: "Zentraler Einstieg für Tokens, Keys und Extension-Zugänge." },
  { title: "Module", path: "/modules", icon: Boxes, text: "Gebündelte HydraHive-Funktionen installieren und prüfen." },
  { title: "Plugins", path: "/plugins", icon: CircuitBoard, text: "Agent-Tools und Plugin-Status verwalten." },
]

export function AdminCockpitPage() {
  const [overlay, setOverlay] = useState<AdminOverlayId | null>(null)

  // Kachel-Klick: existiert ein Cockpit-Overlay für die Action → einrasten,
  // sonst (noch) die bestehende Legacy-Seite öffnen.
  const openArea = (actionId: string, path: string) => {
    const target = OVERLAY_BY_ACTION[actionId]
    if (target) setOverlay(target)
    else openLocalPath(path)
  }

  // Pfad-basierte Kacheln (Ops/Integrationen): Overlay wenn gemappt, sonst Pfad.
  const openPath = (path: string) => {
    const target = OVERLAY_BY_PATH[path]
    if (target) setOverlay(target)
    else openLocalPath(path)
  }

  return (
    <CockpitShell
      eyebrow="Admin"
      title="Admin-Cockpit"
      description="Schaltzentrale für System, User, Module, Integrationen, Credentials und Infrastruktur. Die Route bleibt durch AdminGuard geschützt."
      actions={<CockpitButton tone="primary" onClick={() => openLocalPath("/system")}>System öffnen</CockpitButton>}
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="admin" context="Admin" action={{ label: "System öffnen", path: "/system" }} />
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] xl:grid-cols-[280px_minmax(520px,1fr)_370px]">
        <aside className="space-y-[10px]">
          <CockpitPanel title="Admin-Bereiche" eyebrow="Control">
            <div className="space-y-2">
              {adminLinks.map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.path}
                    onClick={() => openArea(item.id, item.path)}
                    className="group flex w-full items-start gap-3 rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left transition-colors hover:border-[#46617f] hover:bg-[#172133]"
                  >
                    <Icon size={18} className="mt-0.5 text-[#69d7ff]" />
                    <span>
                      <span className="block text-sm font-bold text-[#e8eef8]">{item.title}</span>
                      <span className="mt-1 block text-xs leading-4 text-[#8d9ab0]">{item.desc}</span>
                    </span>
                  </button>
                )
              })}
            </div>
          </CockpitPanel>
        </aside>

        <main className="space-y-[10px]">
          <CockpitPanel title="Betriebszentrale" eyebrow="Ops">
            <div className="grid gap-2 md:grid-cols-3">
              {opsLinks.map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.path}
                    onClick={() => openPath(item.path)}
                    className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left hover:border-[#46617f] hover:bg-[#172133]"
                  >
                    <Icon size={18} className="mb-3 text-[#69d7ff]" />
                    <span className="text-sm font-bold text-[#e8eef8]">{item.title}</span>
                  </button>
                )
              })}
            </div>
          </CockpitPanel>

          <CockpitPanel title="Sicherheitsregeln" eyebrow="Guard">
            <div className="rounded-[4px] border border-amber-400/20 bg-amber-500/[6%] p-4">
              <div className="mb-3 flex items-center gap-2">
                <ShieldAlert size={18} className="text-amber-300" />
                <h3 className="text-sm font-black text-[#e8eef8]">Keine gefährlichen Aktionen beim Laden</h3>
              </div>
              <p className="text-sm leading-5 text-[#d7deea]">
                Das Admin-Cockpit bündelt Einstiege, führt aber keine Wartung, Installationen, Backups, Deletes oder Secrets-Reads automatisch aus. Kritische Aktionen bleiben in den vorhandenen Admin-Seiten und deren Guards.
              </p>
              <div className="mt-4 grid gap-2 md:grid-cols-2">
                {[
                  "Credentials bleiben maskiert.",
                  "Module/Extensions nur per explizitem Klick.",
                  "Backups/Restore bleiben in Systemkarten.",
                  "Logs und Status werden nicht breit gepollt.",
                ].map((item) => <div key={item} className="rounded-[4px] border border-white/[8%] bg-white/[3%] p-2 text-xs text-[#8d9ab0]">• {item}</div>)}
              </div>
            </div>
          </CockpitPanel>

          <CockpitPanel title="Integrationen" eyebrow="Connect">
            <div className="grid gap-2 md:grid-cols-4">
              {integrationLinks.map((item) => {
                const Icon = item.icon
                return (
                  <button key={item.title} onClick={() => openPath(item.path)} className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left hover:border-[#46617f] hover:bg-[#172133]">
                    <Icon size={16} className="mb-2 text-[#69d7ff]" />
                    <h3 className="text-sm font-bold text-[#e8eef8]">{item.title}</h3>
                    <p className="mt-1 text-xs leading-4 text-[#8d9ab0]">{item.text}</p>
                  </button>
                )
              })}
            </div>
          </CockpitPanel>

          <CockpitPanel title="Wartung & Backups" eyebrow="Recovery">
            <div className="grid gap-2 md:grid-cols-2">
              <Info title="Backup" icon={DatabaseBackup} text="Backup/Restore bleibt im Systembereich, damit bestehende Confirmations und Guards greifen." path="/system" />
              <Info title="System-Settings" icon={SlidersHorizontal} text="Globale Einstellungen und Migrationen bleiben geschützt unter /system/settings." path="/system/settings" />
            </div>
          </CockpitPanel>
        </main>

        <aside className="space-y-[10px]">
          <CockpitPanel title="Status" eyebrow="Admin">
            <CockpitSectionLabel>Design</CockpitSectionLabel>
            <p className="mt-2 text-sm leading-5 text-[#d7deea]">
              Admin ist jetzt kein leerer Platzhalter mehr. Es ist die strukturierte Startseite für vorhandene Admin- und Infrastruktur-Module.
            </p>
          </CockpitPanel>

          <CockpitPanel title="Optionale KI" eyebrow="Explizit">
            <p className="text-xs leading-4 text-[#8d9ab0]">Admin-Kacheln öffnen lokale Seiten und starten keine Analyse. KI-Hilfe ist ein bewusst separater Schritt.</p>
            <CockpitButton onClick={() => openLocalPath(explicitAiActions.find((action) => action.id === "admin-agent")?.path ?? "/buddy")} className="mt-3">Admin-Agent bewusst öffnen</CockpitButton>
          </CockpitPanel>

          <CockpitPanel title="Nächste Ausbaustufen" eyebrow="Roadmap">
            <ol className="space-y-2 text-xs leading-4 text-[#8d9ab0]">
              <li><span className="font-semibold text-[#e8eef8]">1.</span> Kompakte Live-Systemmetriken einbinden.</li>
              <li><span className="font-semibold text-[#e8eef8]">2.</span> Modul-/Extension-Health als Ampel.</li>
              <li><span className="font-semibold text-[#e8eef8]">3.</span> Audit-/Log-Panel mit klaren Filtern.</li>
              <li><span className="font-semibold text-[#e8eef8]">4.</span> Integrationsübersicht für GitHub, Gitea, Tailscale, Webmin.</li>
            </ol>
          </CockpitPanel>
        </aside>
      </div>

      {overlay === "users" && <UsersOverlay onClose={() => setOverlay(null)} />}
      {overlay === "modules" && <ModulesOverlay onClose={() => setOverlay(null)} />}
      {overlay === "plugins" && <PluginsOverlay onClose={() => setOverlay(null)} />}
      {overlay === "credentials" && <CredentialsOverlay onClose={() => setOverlay(null)} />}
      {overlay === "themes" && <ThemesOverlay onClose={() => setOverlay(null)} />}
      {overlay === "mcp" && <McpOverlay onClose={() => setOverlay(null)} />}
      {overlay === "llm" && <LlmOverlay onClose={() => setOverlay(null)} />}
    </CockpitShell>
  )
}

function Info({ title, text, path, icon: Icon }: { title: string; text: string; path: string; icon: ComponentType<{ size?: number; className?: string }> }) {
  return (
    <button onClick={() => openLocalPath(path)} className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left hover:border-[#46617f] hover:bg-[#172133]">
      <div className="mb-2 flex items-center gap-2">
        <Icon size={16} className="text-[#69d7ff]" />
        <h3 className="text-sm font-bold text-[#e8eef8]">{title}</h3>
      </div>
      <p className="text-xs leading-4 text-[#8d9ab0]">{text}</p>
    </button>
  )
}
