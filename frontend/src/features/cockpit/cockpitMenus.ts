import { Brain, Clapperboard, FolderKanban, LockKeyhole, ShieldCheck } from "lucide-react"
import type { CockpitMenuItem } from "./CockpitHeaderMenu"

export function cockpitMenu(active: "projects" | "buddy" | "media" | "vault" | "admin"): CockpitMenuItem[] {
  return [
    { label: "Projekte", path: "/projects", icon: FolderKanban, active: active === "projects" },
    { label: "Buddy", path: "/buddy", icon: Brain, active: active === "buddy" },
    { label: "Media", path: "/media", icon: Clapperboard, active: active === "media" },
    { label: "Vault", path: "/vault", icon: LockKeyhole, active: active === "vault" },
    { label: "Admin", path: "/admin", icon: ShieldCheck, active: active === "admin" },
  ]
}
