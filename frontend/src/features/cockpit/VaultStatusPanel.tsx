import { CircleCheck, CircleDashed } from "lucide-react"
import { CockpitPanel } from "./CockpitPanel"

// Ehrlicher Stand (12.10.2026). Nur Aussagen, die im Code belegt sind:
// - Schutzstufen privat/gesundheit im Agenten-Gedächtnis: db/_mirror_levels.py, docs/specs/datamining-access.md
//   (Standard: Projekt-Agenten/Spezialisten nur eigenes Projekt ohne sensibel; Buddy/Master alles des Nutzers)
// - Außenwirkung höchstens normal (Master ausgenommen): db/_mirror_groups.py OUTWARD_TOOLS
// - Freigaben je Modul: access/ (module.<id>), Agenten erben die Rechte des Besitzers: access/tool_filter.py
// - Zugangsdaten nie im Klartext an Agenten: credentials/__init__.py (fetch_url-Injection) + Egress-Redaction
const ACTIVE = [
  "Projekt-Agenten und Spezialisten kommen standardmäßig nicht an Gesundheits- und Privatdaten. Dein Buddy darf alles von dir.",
  "Projekt-Agenten mit Außenwirkung (Mail, Discord, Shell …) kommen nie an Gesundheits- oder Privatdaten.",
  "Jedes Modul kann eine eigene Freigabe verlangen. Agenten haben nur die Rechte ihres Nutzers.",
  "Zugangsdaten benutzen Agenten, ohne sie im Klartext zu sehen.",
]

const PLANNED = [
  "Vault-PIN: Bereiche erst nach PIN öffnen, nach einer Pause wieder gesperrt.",
  "Protokoll: wer hat wann die Akte geöffnet, exportiert oder gelöscht.",
  "Vault-Chat: ein Agent, der die Akte lesen darf, aber nichts nach außen schicken kann.",
  "Befunde als PDF oder Foto hochladen und durchsuchen.",
]

export function VaultStatusPanel() {
  return (
    <>
      <CockpitPanel title="Schon aktiv" eyebrow="Schutz">
        <ul className="space-y-2">
          {ACTIVE.map((t) => (
            <li key={t} className="flex gap-2 text-xs leading-4 text-[#d7deea]">
              <CircleCheck size={14} className="mt-px shrink-0 text-emerald-300" />{t}
            </li>
          ))}
        </ul>
      </CockpitPanel>
      <CockpitPanel title="In Arbeit" eyebrow="Geplant">
        <ul className="space-y-2">
          {PLANNED.map((t) => (
            <li key={t} className="flex gap-2 text-xs leading-4 text-[#8d9ab0]">
              <CircleDashed size={14} className="mt-px shrink-0 text-amber-300" />{t}
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[11px] text-[#68758a]">
          Bis die PIN da ist, schützt der normale Login. Die Bereiche sind noch nicht zusätzlich gesperrt.
        </p>
      </CockpitPanel>
    </>
  )
}
