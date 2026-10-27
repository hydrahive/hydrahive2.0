import { BRAND } from "./brand"

export { BRAND }

interface Props {
  /** wordmark = Hydra + Schriftzug; emblem = Hydra im Wabenrahmen; responsive = Emblem schmal, Schriftzug ab md. */
  variant: "wordmark" | "emblem" | "responsive"
  className?: string
}

/** Das HydraHive-Logo mit der bunten Hydra – ein Baustein für Kopfzeile, Anmeldung usw. */
export function HydraLogo({ variant, className = "" }: Props) {
  if (variant === "responsive") {
    return (
      <>
        <img src={BRAND.emblem} alt="HydraHive" draggable={false} className={`h-9 w-9 select-none md:hidden ${className}`} />
        <img src={BRAND.wordmark} alt="HydraHive" draggable={false} className={`hidden h-9 w-auto select-none md:block ${className}`} />
      </>
    )
  }
  const src = variant === "wordmark" ? BRAND.wordmark : BRAND.emblem
  return <img src={src} alt="HydraHive" draggable={false} className={`select-none ${variant === "wordmark" ? "h-9 w-auto" : ""} ${className}`} />
}
