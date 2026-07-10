import type { ComponentType } from "react"
import { Activity, BrainCircuit, Coins, FileSearch, FileText, FolderHeart, KeyRound, LockKeyhole, Pickaxe, ShieldCheck, StickyNote, Wallet } from "lucide-react"
import { CockpitButton } from "./CockpitButton"
import { CockpitPanel, CockpitSectionLabel } from "./CockpitPanel"
import { CockpitShell } from "./CockpitShell"
import { CockpitTopbar } from "./CockpitTopbar"
import { explicitAiActions, openLocalPath, vaultOfflineActions } from "./actionRegistry"

const vaultAreas = [
  { title: "Patientenakte", path: "/akte", icon: FolderHeart, desc: "Diagnosen, Medikamente, Laborwerte, FHIR/eGA und medizinische Timeline.", tone: "rose" },
  { title: "Crypto Board", path: "/cryptoboard", icon: Coins, desc: "Portfolio, Watchlist, Wallets, Trades, Alerts und Marktanalyse.", tone: "amber" },
  { title: "Scratchpad", path: "/scratchpad", icon: StickyNote, desc: "Persönliche Notizen und Agent-Notizen getrennt halten.", tone: "cyan" },
  { title: "Credentials", path: "/credentials", icon: KeyRound, desc: "API-Keys, Tokens und Zugangsdaten sicher verwalten.", tone: "violet" },
]

const intelligenceLinks = [
  { title: "Datamining", path: "/datamining", icon: Pickaxe, desc: "Historie und Sessions gezielt durchsuchen — nur nach User-Aktion." },
  { title: "Memory", path: "/memory", icon: BrainCircuit, desc: "Langzeitgedächtnis prüfen und kuratieren." },
]

const guardrails = [
  "Keine automatischen Exporte sensibler Daten.",
  "Kein automatisches Datamining beim Laden.",
  "Medizinische Daten getrennt von generischer Recherche behandeln.",
  "Credentials und Wallet-Informationen nie in Logs oder Chat-Meta anzeigen.",
]

const actionLinks = [
  { title: "Befunde suchen", path: "/akte", icon: FileSearch, text: "Medizinische Timeline und Einträge öffnen." },
  { title: "Portfolio prüfen", path: "/cryptoboard", icon: Wallet, text: "Crypto-Daten im spezialisierten Modul bearbeiten." },
  { title: "Private Notiz", path: "/scratchpad", icon: StickyNote, text: "Scratchpad ohne automatische KI-Auswertung öffnen." },
  { title: "Secrets verwalten", path: "/credentials", icon: KeyRound, text: "Credentials-Seite mit Maskierung und Guards verwenden." },
]

export function VaultCockpitPage() {
  return (
    <CockpitShell
      eyebrow="Vault"
      title="Vault-Cockpit"
      description="Sensible Bereiche an einem Ort: Patientenakte, Crypto, Dokumente, Notizen, Credentials und private Historie — mit klaren Schutzplanken."
      actions={<CockpitButton tone="primary" onClick={() => openLocalPath("/akte")}>Meine Akte öffnen</CockpitButton>}
      className="flex h-[100dvh] min-h-0 flex-col overflow-hidden bg-[#080b11]"
      hideHeader
    >
      <CockpitTopbar active="vault" context="gesperrt nach 15 min" action={{ label: "Meine Akte", path: "/akte" }} />
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-hidden p-[10px] xl:grid-cols-[280px_minmax(520px,1fr)_360px]">
        <aside className="space-y-[10px]">
          <CockpitPanel title="Vault-Bereiche" eyebrow="Privat">
            <div className="space-y-2">
              {vaultAreas.map((area) => {
                const Icon = area.icon
                return (
                  <button
                    key={area.path}
                    onClick={() => openLocalPath(area.path)}
                    className="group flex w-full items-start gap-3 rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left transition-colors hover:border-[#46617f] hover:bg-[#172133]"
                  >
                    <Icon size={18} className="mt-0.5 text-[#69d7ff]" />
                    <span className="min-w-0">
                      <span className="block text-sm font-bold text-[#e8eef8]">{area.title}</span>
                      <span className="mt-1 block text-xs leading-4 text-[#8d9ab0]">{area.desc}</span>
                    </span>
                  </button>
                )
              })}
            </div>
          </CockpitPanel>

          <CockpitPanel title="Intelligence" eyebrow="Suche">
            <div className="space-y-2">
              {intelligenceLinks.map((item) => {
                const Icon = item.icon
                return (
                  <button
                    key={item.path}
                    onClick={() => openLocalPath(item.path)}
                    className="flex w-full items-start gap-3 rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left hover:border-[#46617f] hover:bg-[#172133]"
                  >
                    <Icon size={17} className="mt-0.5 text-[#69d7ff]" />
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
          <CockpitPanel title="Sicherheitszonen" eyebrow="Scope">
            <div className="grid gap-2 md:grid-cols-3">
              <Zone title="Medizin" icon={Activity} text="Akte, eGA, FHIR, Befunde und medizinische Notizen." />
              <Zone title="Finanzen & Crypto" icon={Wallet} text="Portfolio, Wallets, Trades, Watchlists und Alerts." />
              <Zone title="Private Daten" icon={FileText} text="Notizen, Dokumente, Credentials und Verlaufssuche." />
            </div>
          </CockpitPanel>

          <CockpitPanel title="Vault-Prinzip" eyebrow="Schutz">
            <div className="rounded-[4px] border border-emerald-400/20 bg-emerald-500/[6%] p-4">
              <div className="mb-3 flex items-center gap-2">
                <ShieldCheck size={18} className="text-emerald-300" />
                <h3 className="text-sm font-black text-[#e8eef8]">Alles auf Klick — nichts automatisch</h3>
              </div>
              <p className="text-sm leading-5 text-[#d7deea]">
                Der Vault bündelt sensible Systeme, startet aber beim Laden keine Datenexporte, keine breite Suche und keine LLM-Auswertung. Jede Analyse bleibt eine bewusste User-Aktion.
              </p>
              <div className="mt-4 grid gap-2 md:grid-cols-2">
                {guardrails.map((item) => (
                  <div key={item} className="rounded-[4px] border border-white/[8%] bg-white/[3%] p-2 text-xs text-[#8d9ab0]">• {item}</div>
                ))}
              </div>
            </div>
          </CockpitPanel>

          <CockpitPanel title="Bewusste Aktionen" eyebrow="Launchpad">
            <div className="grid gap-2 md:grid-cols-4">
              {actionLinks.map((item) => {
                const Icon = item.icon
                return (
                  <button key={item.title} onClick={() => openLocalPath(item.path)} className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left hover:border-[#46617f] hover:bg-[#172133]">
                    <Icon size={16} className="mb-2 text-[#69d7ff]" />
                    <h3 className="text-sm font-bold text-[#e8eef8]">{item.title}</h3>
                    <p className="mt-1 text-xs leading-4 text-[#8d9ab0]">{item.text}</p>
                  </button>
                )
              })}
            </div>
          </CockpitPanel>

          <CockpitPanel title="Dokumente & Suche" eyebrow="Vorbereitung">
            <div className="mb-3 flex flex-wrap gap-2">{vaultOfflineActions.filter((action) => action.kind === "status-only").map((action) => <span key={action.id} className="rounded-[4px] border border-amber-400/20 bg-amber-500/[6%] px-2 py-1 text-[11px] text-amber-100">{action.label}: geplant</span>)}</div>
            <div className="grid gap-2 md:grid-cols-2">
              <div className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3">
                <h3 className="text-sm font-bold text-[#e8eef8]">Patientenakte-Dokumente</h3>
                <p className="mt-1 text-xs leading-4 text-[#8d9ab0]">PDF/Text/OCR/FTS bleibt als eigener Port-Task geplant, damit Upload-Guards und medizinische Trennung sauber bleiben.</p>
              </div>
              <div className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3">
                <h3 className="text-sm font-bold text-[#e8eef8]">Private Verlaufssuche</h3>
                <p className="mt-1 text-xs leading-4 text-[#8d9ab0]">Datamining und Memory sind verlinkt, aber nicht automatisch aktiv. Keine Tokenfresser im Vault-Load.</p>
              </div>
            </div>
          </CockpitPanel>
        </main>

        <aside className="space-y-[10px]">
          <CockpitPanel title="Status" eyebrow="Vault">
            <CockpitSectionLabel>Design</CockpitSectionLabel>
            <p className="mt-2 text-sm leading-5 text-[#d7deea]">
              Vault ist jetzt ein echter Einstiegspunkt für sensible Bereiche. Die volle Dokumenten- und Sicherheitslogik kommt in Folgeetappen.
            </p>
          </CockpitPanel>

          <CockpitPanel title="Optionale KI" eyebrow="Explizit">
            <p className="text-xs leading-4 text-[#8d9ab0]">Vault lädt keine sensiblen Daten in einen Chat. KI-Auswertung bleibt ein bewusst gestarteter, separater Schritt.</p>
            <CockpitButton onClick={() => openLocalPath(explicitAiActions.find((action) => action.id === "vault-agent")?.path ?? "/buddy")} className="mt-3">Vault-Agent bewusst öffnen</CockpitButton>
          </CockpitPanel>

          <CockpitPanel title="Nächste Ausbaustufen" eyebrow="Roadmap">
            <ol className="space-y-2 text-xs leading-4 text-[#8d9ab0]">
              <li><span className="font-semibold text-[#e8eef8]">1.</span> Vault-Lock/Unlock und Timeout-Konzept.</li>
              <li><span className="font-semibold text-[#e8eef8]">2.</span> Patientenakte Dokumente/PDF/FTS portieren.</li>
              <li><span className="font-semibold text-[#e8eef8]">3.</span> Vault-Chat mit Kontext-Guard.</li>
              <li><span className="font-semibold text-[#e8eef8]">4.</span> Audit sensibler Aktionen.</li>
            </ol>
          </CockpitPanel>

          <CockpitPanel title="Sicherheitsmodus" eyebrow="Guard">
            <div className="flex items-start gap-3 rounded-[4px] border border-amber-400/20 bg-amber-500/[6%] p-3">
              <LockKeyhole size={18} className="mt-0.5 text-amber-300" />
              <p className="text-xs leading-4 text-[#d7deea]">Aktuell Soft-Guard: sensible Bereiche sind verlinkt, aber nicht verschmolzen. Harte Sperren folgen vor produktiver Vault-Konsolidierung.</p>
            </div>
          </CockpitPanel>
        </aside>
      </div>
    </CockpitShell>
  )
}

function Zone({ title, text, icon: Icon }: { title: string; text: string; icon: ComponentType<{ size?: number; className?: string }> }) {
  return (
    <div className="rounded-[4px] border border-[#2a364b] bg-[#111827] p-3">
      <div className="mb-2 flex items-center gap-2">
        <Icon size={16} className="text-[#69d7ff]" />
        <h3 className="text-sm font-black text-[#e8eef8]">{title}</h3>
      </div>
      <p className="text-xs leading-4 text-[#8d9ab0]">{text}</p>
    </div>
  )
}
