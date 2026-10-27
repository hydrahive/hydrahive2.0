import { BrainCircuit, Pickaxe, ShieldCheck } from "lucide-react"
import { moduleNavOwners } from "@/modules/index.generated"
import { useMyAccess } from "@/features/access/useMyAccess"
import { CockpitPanel } from "./CockpitPanel"
import { CockpitShell } from "./CockpitShell"
import { CockpitTopbar } from "./CockpitTopbar"
import { openLocalPath } from "./actionRegistry"
import { visibleVaultAreas } from "./vaultAreas"
import { VaultStatusPanel } from "./VaultStatusPanel"

const historyLinks = [
  { title: "Datamining", path: "/datamining", icon: Pickaxe, desc: "Frühere Gespräche durchsuchen – nur wenn du suchst." },
  { title: "Gedächtnis", path: "/memory", icon: BrainCircuit, desc: "Gemerkte Fakten deiner Agenten prüfen und löschen." },
]

/** Vault: Einstieg in sensible Bereiche. Zeigt nur installierte, freigegebene Bereiche und ehrlich,
 *  welcher Schutz heute greift und was noch kommt (docs/specs/vault.md). Lädt selbst keine sensiblen Daten. */
export function VaultCockpitPage() {
  const access = useMyAccess()
  const areas = visibleVaultAreas(moduleNavOwners, access)
  return (
    <CockpitShell eyebrow="Vault" title="Vault-Cockpit" hideHeader
      description="Sensible Bereiche an einem Ort: Gesundheit, Finanzen und Zugangsdaten."
      className="flex h-full min-h-0 flex-col overflow-hidden bg-[#080b11]">
      <CockpitTopbar active="vault" context="Sensible Bereiche · PIN-geschützt" />
      <div className="grid min-h-0 flex-1 gap-[10px] overflow-y-auto p-[10px] xl:grid-cols-[minmax(420px,1fr)_380px] xl:overflow-hidden">
        <main className="min-h-0 space-y-[10px] overflow-y-auto">
          <CockpitPanel theme="kontakt" title="Deine sensiblen Bereiche" eyebrow="Vault">
            {areas.length === 0 ? (
              <p className="text-sm text-[#8d9ab0]">
                Noch keine sensiblen Module installiert. Meine Akte, Cryptoboard und Haushaltsbuch installiert der Admin
                unter Einstellungen → Module.
              </p>
            ) : (
              <div className="grid gap-2 md:grid-cols-2">
                {areas.map(({ id, title, path, icon: Icon, desc }) => (
                  <button key={id} onClick={() => openLocalPath(path)}
                    className="flex items-start gap-3 rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left hover:border-[#46617f] hover:bg-[#172133]">
                    <Icon size={18} className="mt-0.5 text-[#69d7ff]" />
                    <span className="min-w-0">
                      <span className="block text-sm font-bold text-[#e8eef8]">{title}</span>
                      <span className="mt-1 block text-xs leading-4 text-[#8d9ab0]">{desc}</span>
                    </span>
                  </button>
                ))}
              </div>
            )}
          </CockpitPanel>

          <CockpitPanel theme="status" title="Verlauf" eyebrow="Suche">
            <div className="grid gap-2 md:grid-cols-2">
              {historyLinks.map(({ title, path, icon: Icon, desc }) => (
                <button key={path} onClick={() => openLocalPath(path)}
                  className="flex items-start gap-3 rounded-[4px] border border-[#2a364b] bg-[#111827] p-3 text-left hover:border-[#46617f] hover:bg-[#172133]">
                  <Icon size={17} className="mt-0.5 text-[#69d7ff]" />
                  <span>
                    <span className="block text-sm font-bold text-[#e8eef8]">{title}</span>
                    <span className="mt-1 block text-xs leading-4 text-[#8d9ab0]">{desc}</span>
                  </span>
                </button>
              ))}
            </div>
          </CockpitPanel>

          <CockpitPanel theme="wissen" title="Grundsatz" eyebrow="Schutz">
            <div className="flex items-start gap-3 rounded-[4px] border border-emerald-400/20 bg-emerald-500/[6%] p-3">
              <ShieldCheck size={18} className="mt-0.5 text-emerald-300" />
              <p className="text-sm leading-5 text-[#d7deea]">
                Diese Seite lädt keine sensiblen Daten und startet keine KI. Alles passiert erst, wenn du einen Bereich
                öffnest – dann fragt der Vault nach deiner PIN.
              </p>
            </div>
          </CockpitPanel>
        </main>
        <aside className="min-h-0 space-y-[10px] overflow-y-auto">
          <VaultStatusPanel />
        </aside>
      </div>
    </CockpitShell>
  )
}
