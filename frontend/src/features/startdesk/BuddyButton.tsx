// Schnellsprung zum Buddy auf der Startseite (docs/specs/startdesktop.md).
// Bild: Ausschnitt aus public/buddy-media/buddy-success.mp4 (Hydra jubelt) – ohne KI erzeugt.
import { MessageCircleHeart } from "lucide-react"

export function BuddyButton({ onOpen }: { onOpen: () => void }) {
  return (
    <div className="mt-5 flex justify-center">
      <button type="button" onClick={onOpen} aria-label="Mit Buddy sprechen"
        className="group relative w-full max-w-2xl overflow-hidden rounded-[10px] border border-[#ff6fae]/40 text-left shadow-lg shadow-black/40 transition hover:-translate-y-0.5 hover:border-[#ff9cc8]/70 hover:shadow-xl hover:shadow-[#ff6fae]/10">
        <img src="/startdesk/buddy-knopf.webp" alt="" className="h-[120px] w-full object-cover object-[50%_35%] transition duration-300 group-hover:scale-[1.03] sm:h-[150px]" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#080b11]/90 via-[#080b11]/35 to-transparent" />
        <div className="absolute inset-y-0 left-0 flex flex-col justify-center gap-1 px-4 sm:px-6">
          <span className="flex items-center gap-2 text-xl font-black text-[#e8eef8] drop-shadow sm:text-2xl">
            <MessageCircleHeart size={22} className="text-[#ff9cc8]" /> Buddy
          </span>
          <span className="text-xs font-semibold text-[#e8eef8]/85 drop-shadow sm:text-sm">Einfach fragen – ich helfe dir weiter</span>
        </div>
      </button>
    </div>
  )
}
