// „Aktiver Buddy“-Karte (Task 0dda5420, Etappe Buddy): Tills Hydra am Schreibtisch als Hintergrund,
// darüber der Name; darunter die fünf Köpfe als kleine Tags mit ihren Charakteren.
import { HEAD_TAGS } from "./_buddyHeads"

export function BuddyHero({ agentName }: { agentName: string }) {
  return (
    <div className="overflow-hidden rounded-[6px] border border-[#2a364b] bg-[#0d1420]">
      <div className="relative h-[160px]">
        <img src="/hydra/schreibtisch.webp" alt="" loading="lazy" draggable={false}
          className="absolute inset-0 h-full w-full select-none object-cover object-center" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0d1420] via-[#0d1420]/55 to-transparent" />
        <div className="absolute inset-x-3 bottom-2.5">
          <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-[#69d7ff] drop-shadow">Aktiver Buddy</div>
          <div className="truncate text-sm font-black text-[#e8eef8] drop-shadow">{agentName}</div>
        </div>
      </div>
      <div className="flex items-end justify-between gap-1 px-3 pb-2.5 pt-1.5">
        {HEAD_TAGS.map((h) => (
          <span key={h.name} title={h.name}
            className={`flex flex-col items-center gap-0.5 rounded-[6px] border px-1 pb-1 pt-0.5 transition hover:-translate-y-0.5 ${h.tone}`}>
            <img src={h.src} alt="" loading="lazy" draggable={false} className="h-8 w-auto select-none drop-shadow-[0_2px_4px_rgba(0,0,0,0.5)]" />
            <span className="text-[9px] font-bold leading-none">{h.name}</span>
          </span>
        ))}
      </div>
    </div>
  )
}
