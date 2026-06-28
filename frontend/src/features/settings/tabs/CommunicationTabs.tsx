import { DiscordCard } from "@/features/communication/DiscordCard"
import { WhatsAppCard } from "@/features/communication/WhatsAppCard"

/**
 * Tab-Inhalte der Gruppe "Kommunikation" — je Kanal eine Karteikarte.
 * (Mail liegt in den globalen Settings-Werten, Gruppe "Mail".)
 */
export function CommDiscord() {
  return <div className="space-y-4"><DiscordCard /></div>
}

export function CommWhatsApp() {
  return <div className="space-y-4"><WhatsAppCard /></div>
}
