import { Link } from "react-router-dom"
import { ExternalLink } from "lucide-react"
import { BackupCard } from "@/features/system/BackupCard"
import { BridgeCard } from "@/features/system/BridgeCard"

/** Tab-Inhalte der Gruppe "System". */
export function SysBackup() {
  return <div className="space-y-4"><BackupCard /></div>
}

export function SysBridge() {
  return <div className="space-y-4"><BridgeCard /></div>
}

/**
 * Status/Allgemein (Stats, Uptime, Pfade, Health) lebt von Live-Daten, die die
 * SystemPage als Ganzes lädt — als Übersicht am Stück sinnvoller. Daher hier ein
 * klarer Verweis statt halber Einbettung.
 */
export function SysStatus() {
  return (
    <div className="rounded-xl border border-white/8 bg-zinc-900/40 p-6">
      <h3 className="text-base font-semibold text-zinc-100">System-Status & Übersicht</h3>
      <p className="mt-2 text-sm text-zinc-400">
        Live-Statistiken, Uptime, Speicher und Health-Checks gibt es gebündelt auf
        der System-Übersicht.
      </p>
      <Link
        to="/system"
        className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-[#104E8B]/30 px-3.5 py-2 text-sm text-sky-200 ring-1 ring-inset ring-[#104E8B]/50 hover:bg-[#104E8B]/40 transition-colors"
      >
        <ExternalLink size={14} />
        System-Übersicht öffnen
      </Link>
    </div>
  )
}
