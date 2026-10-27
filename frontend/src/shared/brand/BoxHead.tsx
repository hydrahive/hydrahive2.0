import { BOX_THEMES, type BoxTheme } from "./boxThemes"

/** Kleiner Hydra-Kopf im Kopf einer Box/eines Fensters – reine Deko, der Titel trägt die Bedeutung. */
export function BoxHead({ theme }: { theme: BoxTheme }) {
  const t = BOX_THEMES[theme]
  return (
    <span title={t.name} className={`relative h-[46px] w-[46px] shrink-0 overflow-hidden rounded-full border ${t.ring}`}>
      {/* Maße gemessen (Till 27.10.: Köpfe waren abgeschnitten): bei Kreis 46 / Bild 42 / oben 5 px liegt bei allen
          fünf Köpfen das ganze Fell mit Abstand im Kreis, nur der Hals verschwindet unten. */}
      <img src={t.head} alt="" aria-hidden="true" loading="lazy" draggable={false}
        className="absolute left-1/2 top-[5px] h-[42px] w-auto max-w-none -translate-x-1/2 select-none" />
    </span>
  )
}
