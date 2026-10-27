import { BOX_THEMES, type BoxTheme } from "./boxThemes"

/** Kleiner Hydra-Kopf im Kopf einer Box/eines Fensters – reine Deko, der Titel trägt die Bedeutung. */
export function BoxHead({ theme }: { theme: BoxTheme }) {
  const t = BOX_THEMES[theme]
  return (
    <span title={t.name} className={`relative h-9 w-9 shrink-0 overflow-hidden rounded-full border ${t.ring}`}>
      {/* Bild größer als der Kreis und oben angesetzt: das Gesicht füllt den Kreis, der Hals wird abgeschnitten. */}
      <img src={t.head} alt="" aria-hidden="true" loading="lazy" draggable={false}
        className="absolute left-1/2 top-[1px] h-[50px] w-auto max-w-none -translate-x-1/2 select-none" />
    </span>
  )
}
