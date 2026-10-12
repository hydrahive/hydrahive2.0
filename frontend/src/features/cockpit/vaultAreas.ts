// Vault-Bereiche: nur zeigen, was installiert ist und freigegeben wurde (keine toten Links).
import type { ComponentType } from "react"
import { Coins, FolderHeart, KeyRound, PiggyBank } from "lucide-react"
import { pathAllowed } from "@/features/access/navAccess"
import type { MyAccess } from "@/features/access/types"

export interface VaultArea {
  id: string
  title: string
  path: string
  icon: ComponentType<{ size?: number; className?: string }>
  desc: string
  /** Modul-ID, wenn der Bereich ein Modul ist (sonst Kern-Funktion, immer vorhanden). */
  module?: string
}

export const VAULT_AREAS: VaultArea[] = [
  { id: "akte", title: "Meine Akte", path: "/akte", icon: FolderHeart, module: "patientenakte",
    desc: "Diagnosen, Medikamente, Laborwerte, Arztbesuche – Import aus FHIR und der elektronischen Akte." },
  { id: "cryptoboard", title: "Cryptoboard", path: "/cryptoboard", icon: Coins, module: "cryptoboard",
    desc: "Portfolio, Wallets, Kurse und Watchlist." },
  { id: "haushaltsbuch", title: "Haushaltsbuch", path: "/haushaltsbuch", icon: PiggyBank, module: "haushaltsbuch",
    desc: "Konten, Buchungen, Budgets und Kontoimport." },
  { id: "credentials", title: "Zugangsdaten", path: "/credentials", icon: KeyRound,
    desc: "API-Schlüssel und Passwörter. Agenten benutzen sie, sehen sie aber nie im Klartext." },
]

/** owners: Nav-Pfad → Modul-ID der installierten Module (moduleNavOwners). */
export function visibleVaultAreas(owners: Record<string, string>, access: MyAccess | null): VaultArea[] {
  const installed = new Set(Object.values(owners))
  return VAULT_AREAS.filter((a) => (!a.module || installed.has(a.module)) && pathAllowed(a.path, access, owners))
}
