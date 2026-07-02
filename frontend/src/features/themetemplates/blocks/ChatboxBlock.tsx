import { BuddyPage } from "@/features/buddy/BuddyPage"

/** Baustein-Wrapper für die (self-contained) Buddy-Chatbox.
 *
 *  Die Chatbox will die volle Höhe ihres Containers (`h-full`). Im Template-Fluss
 *  gibt es keine natürliche Höhe, deshalb spannt dieser Wrapper einen definierten
 *  Höhen-Kasten auf. Der Designer steuert die Höhe per Attribut:
 *    <hh-chatbox height="70vh"/>   (Default 70vh)
 *
 *  agent-Attribut ist für später vorgesehen (verschiedene Chat-Kontexte); aktuell
 *  rendert der Baustein den Buddy-Chat, der sich Session/State selbst holt. */
export function ChatboxBlock({ attrs }: { attrs: Record<string, string> }) {
  const height = attrs.height && /^[0-9]+(px|vh|rem|%)$/.test(attrs.height) ? attrs.height : "70vh"
  return (
    <div style={{ height }} className="min-h-[320px]">
      <BuddyPage />
    </div>
  )
}
