import { Link } from "react-router-dom"
import { ExternalLink, Mail } from "lucide-react"
import { DiscordCard } from "@/features/communication/DiscordCard"
import { WhatsAppCard } from "@/features/communication/WhatsAppCard"
import { useAuthStore } from "@/features/auth/useAuthStore"

/**
 * Tab-Inhalte der Gruppe "Kommunikation" — je Kanal eine Karteikarte.
 */
export function CommDiscord() {
  return <div className="space-y-4"><DiscordCard /></div>
}

export function CommWhatsApp() {
  return <div className="space-y-4"><WhatsAppCard /></div>
}

/**
 * Mail (SMTP/IMAP) ist globale Infrastruktur und liegt bei den globalen Settings im
 * Admin-Cockpit (Gruppe „Mail“). Nur Admins bekommen den Link; alle anderen den Hinweis.
 */
export function CommMail() {
  const isAdmin = useAuthStore((s) => s.role) === "admin"
  return (
    <div className="rounded-xl border border-white/8 bg-zinc-900/40 p-6">
      <div className="flex items-center gap-2 text-zinc-200">
        <Mail size={16} />
        <h3 className="text-base font-semibold">E-Mail (SMTP / IMAP)</h3>
      </div>
      <p className="mt-2 text-sm text-zinc-400">
        Die Mail-Zugangsdaten (Versand &amp; Empfang) gelten für das ganze System.
        Sie werden im Admin-Cockpit unter „Globale Settings“, Gruppe „Mail“, eingerichtet.
        {!isAdmin && " Das macht dein Admin."}
      </p>
      {isAdmin && (
        <Link
          to="/admin?section=system-settings"
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-[#104E8B]/30 px-3.5 py-2 text-sm text-sky-200 ring-1 ring-inset ring-[#104E8B]/50 hover:bg-[#104E8B]/40 transition-colors"
        >
          <ExternalLink size={14} />
          Zu den globalen Settings
        </Link>
      )}
    </div>
  )
}
