import type { ReactNode } from "react"
import { Link } from "react-router-dom"
import { CockpitButton } from "./CockpitButton"
import { CockpitPanel } from "./CockpitPanel"
import { CockpitShell } from "./CockpitShell"

interface Props {
  kind: "projects" | "media" | "vault" | "admin"
  title: string
  eyebrow: string
  description: string
  bullets: string[]
  mockupPath?: string
  children?: ReactNode
}

export function CockpitPlaceholderPage({ title, eyebrow, description, bullets, mockupPath, children }: Props) {
  return (
    <CockpitShell
      eyebrow={eyebrow}
      title={title}
      description={description}
      actions={mockupPath && <CockpitButton onClick={() => window.open(mockupPath, "_blank")}>Mockup öffnen</CockpitButton>}
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <CockpitPanel title="Etappe 1" eyebrow="Cockpit-Shell">
          <p className="text-sm leading-6 text-zinc-400">
            Diese Seite ist der stabile Einstiegspunkt für das neue Cockpit. Die alten Seiten bleiben während der Migration weiter erreichbar.
          </p>
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {bullets.map((b) => (
              <div key={b} className="rounded-[4px] border border-white/[8%] bg-white/[3%] p-3 text-sm text-zinc-300">
                {b}
              </div>
            ))}
          </div>
          {children}
        </CockpitPanel>
        <CockpitPanel title="Wichtige Regel" eyebrow="Migration">
          <p className="text-sm leading-6 text-zinc-400">
            Bestehende Funktionen werden eingebettet, nicht neu erfunden. Besonders der Chat bleibt vollständig: Uploads, Tools, Tokens, Slash-Befehle und Vibe-Coding.
          </p>
          <div className="mt-4 flex flex-col gap-2">
            <Link className="text-xs font-bold text-cyan-300 hover:text-cyan-200" to="/werkstatt">Alte Werkstatt öffnen</Link>
            <Link className="text-xs font-bold text-cyan-300 hover:text-cyan-200" to="/settings/projects">Alte Projektverwaltung öffnen</Link>
            <Link className="text-xs font-bold text-cyan-300 hover:text-cyan-200" to="/settings/agents">Alte Agentenverwaltung öffnen</Link>
          </div>
        </CockpitPanel>
      </div>
    </CockpitShell>
  )
}
