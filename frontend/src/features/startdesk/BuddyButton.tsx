// Schnellsprung zum Buddy auf der Startseite (docs/specs/startdesktop.md).
// Bild: Tills bunte Hydra im Arbeitszimmer, rechts im Bild, links Platz für den Text
// (Task 0dda5420). Das Bild hat das Box-Format (4,5:1), die Figur liegt mit Rand darin;
// erzeugt mit generated/hydra-design/box-bilder.py aus entwuerfe/buddy-banner-v1.jpg.
import { MessageCircleHeart } from "lucide-react"

export function BuddyButton({ onOpen }: { onOpen: () => void }) {
  return (
    <div className="mt-5 flex justify-center">
      <button type="button" onClick={onOpen} aria-label="Mit Buddy sprechen"
        className="group relative w-full max-w-2xl overflow-hidden rounded-[10px] border border-[#ff6fae]/40 text-left shadow-lg shadow-black/40 transition hover:-translate-y-0.5 hover:border-[#ff9cc8]/70 hover:shadow-xl hover:shadow-[#ff6fae]/10">
        <img src="/startdesk/buddy-banner.webp" alt="" className="h-[120px] w-full object-cover object-[75%_50%] sm:object-[78%_50%] transition duration-300 group-hover:scale-[1.03] sm:h-[150px]" />
        <div className="absolute inset-0 bg-gradient-to-r from-s-grund/90 via-s-grund/40 via-45% to-transparent to-60%" />
        <div className="absolute inset-y-0 left-0 flex flex-col justify-center gap-1 px-4 sm:px-6">
          <span className="flex items-center gap-2 text-xl font-black text-[#e8eef8] drop-shadow sm:text-2xl">
            <MessageCircleHeart size={22} className="text-[#ff9cc8]" /> Buddy
          </span>
          <span className="max-w-[150px] text-[11px] font-semibold leading-tight text-[#e8eef8]/85 drop-shadow sm:max-w-none sm:text-sm">Einfach fragen – ich helfe dir weiter</span>
        </div>
      </button>
    </div>
  )
}
