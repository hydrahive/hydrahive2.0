// Avatar neben Buddys Antworten: der Buddy-Kopf (mint) von Tills Hydra – klein besser erkennbar als die ganze Figur.
export function BuddyAvatar({ live }: { live: boolean }) {
  return (
    <span className="grid h-[32px] w-[32px] place-items-center overflow-hidden rounded-full border border-[#34d399]/40 bg-[#34d399]/10">
      <img src="/startdesk/koepfe/kopf-1-mint.webp" alt="" draggable={false}
        className={`mt-1 h-[30px] w-auto select-none ${live ? "animate-pulse" : ""}`} />
    </span>
  )
}
