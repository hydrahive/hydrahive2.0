import type { ComponentType } from "react"
import { Boxes, Brain, CircuitBoard, Container, DatabaseBackup, KeyRound, MonitorCog, PlugZap, Server, ShieldAlert, SlidersHorizontal, Users, WandSparkles } from "lucide-react"
import { CockpitButton } from "./CockpitButton"
import { CockpitHeaderMenu } from "./CockpitHeaderMenu"
import { CockpitPanel, CockpitSectionLabel } from "./CockpitPanel"
import { CockpitShell } from "./CockpitShell"
import { cockpitMenu } from "./cockpitMenus"

const adminLinks = [
  { title: "System", path: "/system", icon: Server, desc: "Status, Backup, Samba, Tailscale, AgentLink und Wartung." },
  { title: "User", path: "/users", icon: Users, desc: "Accounts, Rollen und Zugriff." },
  { title: "Module", path: "/modules", icon: Boxes, desc: "HydraHive-Module installieren und aktualisieren." },
  { title: "Extensions", path: "/extensions", icon: PlugZap, desc: "System-Erweiterungen wie Gitea, Ollama oder Dienste." },
  { title: "Plugins", path: "/plugins", icon: CircuitBoard, desc: "Tool-Plugins verwalten." },
  { title: "Credentials", path: "/credentials", icon: KeyRound, desc: "Zugangsdaten sicher speichern — Werte bleiben maskiert." },
]

const opsLinks = [
  { title: "LLM", path: "/llm", icon: Brain },
  { title: "MCP", path: "/mcp", icon: WandSparkles },
  { title: "Skills", path: "/skills", icon: SlidersHorizontal },
  { title: "VMs", path: "/vms", icon: MonitorCog },
  { title: "Container", path: "/containers", icon: Container },
  { title: "Themes", path: "/themes", icon: WandSparkles },
]

export function AdminCockpitPage() {
  return (
    <CockpitShell
      eyebrow="Admin"
      title="Admin-Cockpit"
      description="Schaltzentrale für System, User, Module, Integrationen, Credentials und Infrastruktur. Die Route bleibt durch AdminGuard geschützt."
      menu={<CockpitHeaderMenu items={cockpitMenu("admin")} />}
      actions={<CockpitButton tone="primary" onClick={() => window.open("/system", "_self")}>System öffnen</CockpitButton>}
      className="min-h-[100dvh] bg-[#080b11]"
    >
      <div className="grid gap-[10px] xl:grid-cols-[320px_minmax(420px,1fr)_340px]">
        <aside className="space-y-[10px]">
          <CockpitPanel title="Admin-Bereiche" eyebrow="Control">
            <div className="space-y-2">
              {adminLinks.map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.path}
                    onClick={() => window.open(item.path, "_self")}
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
                    onClick={() => window.open(item.path, "_self")}
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
    </CockpitShell>
  )
}

function Info({ title, text, path, icon: Icon }: { title: string; text: string; path: string; icon: ComponentType<{ size?: number; className?: string }> }) {
  return (
    <button onClick={() => window.open(path, "_self")} className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left hover:border-[#46617f] hover:bg-[#172133]">
      <div className="mb-2 flex items-center gap-2">
        <Icon size={16} className="text-[#69d7ff]" />
        <h3 className="text-sm font-bold text-[#e8eef8]">{title}</h3>
      </div>
      <p className="text-xs leading-4 text-[#8d9ab0]">{text}</p>
    </button>
  )
}
