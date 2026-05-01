/**
 * Domain-Farben (#77) — eine Tailwind-Color pro App-Bereich. Verwendet im
 * Bento-Menü, Sidebar-Akzenten und domain-spezifischen Buttons.
 *
 * Farben gewählt für Differenzierbarkeit auf dunklem Background. Wenn ein
 * neuer Bereich dazukommt: hier eintragen, damit Bento + Sidebar automatisch
 * passen.
 */

export type DomainColor =
  | "blue" | "violet" | "amber" | "emerald" | "fuchsia"
  | "rose" | "sky" | "teal" | "lime" | "yellow"
  | "indigo" | "zinc" | "cyan" | "orange"

export const DOMAIN_COLORS: Record<string, DomainColor> = {
  "/": "indigo",
  "/chat": "blue",
  "/agents": "violet",
  "/projects": "amber",
  "/communication": "lime",
  "/butler": "rose",
  "/vms": "teal",
  "/containers": "sky",
  "/llm": "emerald",
  "/mcp": "fuchsia",
  "/skills": "orange",
  "/credentials": "yellow",
  "/users": "indigo",
  "/plugins": "yellow",
  "/system": "zinc",
  "/help": "cyan",
  "/profile": "violet",
}

export function colorFor(path: string): DomainColor {
  if (DOMAIN_COLORS[path]) return DOMAIN_COLORS[path]
  // Fallback per longest-prefix-match (z.B. /agents/<id>)
  const match = Object.keys(DOMAIN_COLORS)
    .filter(p => p !== "/" && path.startsWith(p))
    .sort((a, b) => b.length - a.length)[0]
  return match ? DOMAIN_COLORS[match] : "violet"
}

// Tailwind-Klassen pro Farbe — Tailwind kann dynamische Klassen-Strings nicht
// treeshaken, deshalb hardcoded Map. Wir nutzen 500/15% bzw. 500/30 als
// Hintergrund/Border für active-States, 400 als Text/Icon-Farbe.
export const DOMAIN_TW: Record<DomainColor, {
  bg: string; bgActive: string; border: string; text: string; textActive: string;
  iconBg: string; iconBgActive: string; iconText: string; iconTextActive: string;
}> = {
  blue:    { bg: "bg-blue-500/[6%]",    bgActive: "bg-blue-500/15",    border: "border-blue-500/30",    text: "text-zinc-400", textActive: "text-blue-200",    iconBg: "bg-white/[5%]", iconBgActive: "bg-blue-500/20",    iconText: "text-blue-300",    iconTextActive: "text-blue-200" },
  violet:  { bg: "bg-violet-500/[6%]",  bgActive: "bg-violet-500/15",  border: "border-violet-500/30",  text: "text-zinc-400", textActive: "text-violet-200",  iconBg: "bg-white/[5%]", iconBgActive: "bg-violet-500/20",  iconText: "text-violet-300",  iconTextActive: "text-violet-200" },
  amber:   { bg: "bg-amber-500/[6%]",   bgActive: "bg-amber-500/15",   border: "border-amber-500/30",   text: "text-zinc-400", textActive: "text-amber-200",   iconBg: "bg-white/[5%]", iconBgActive: "bg-amber-500/20",   iconText: "text-amber-300",   iconTextActive: "text-amber-200" },
  emerald: { bg: "bg-emerald-500/[6%]", bgActive: "bg-emerald-500/15", border: "border-emerald-500/30", text: "text-zinc-400", textActive: "text-emerald-200", iconBg: "bg-white/[5%]", iconBgActive: "bg-emerald-500/20", iconText: "text-emerald-300", iconTextActive: "text-emerald-200" },
  fuchsia: { bg: "bg-fuchsia-500/[6%]", bgActive: "bg-fuchsia-500/15", border: "border-fuchsia-500/30", text: "text-zinc-400", textActive: "text-fuchsia-200", iconBg: "bg-white/[5%]", iconBgActive: "bg-fuchsia-500/20", iconText: "text-fuchsia-300", iconTextActive: "text-fuchsia-200" },
  rose:    { bg: "bg-rose-500/[6%]",    bgActive: "bg-rose-500/15",    border: "border-rose-500/30",    text: "text-zinc-400", textActive: "text-rose-200",    iconBg: "bg-white/[5%]", iconBgActive: "bg-rose-500/20",    iconText: "text-rose-300",    iconTextActive: "text-rose-200" },
  sky:     { bg: "bg-sky-500/[6%]",     bgActive: "bg-sky-500/15",     border: "border-sky-500/30",     text: "text-zinc-400", textActive: "text-sky-200",     iconBg: "bg-white/[5%]", iconBgActive: "bg-sky-500/20",     iconText: "text-sky-300",     iconTextActive: "text-sky-200" },
  teal:    { bg: "bg-teal-500/[6%]",    bgActive: "bg-teal-500/15",    border: "border-teal-500/30",    text: "text-zinc-400", textActive: "text-teal-200",    iconBg: "bg-white/[5%]", iconBgActive: "bg-teal-500/20",    iconText: "text-teal-300",    iconTextActive: "text-teal-200" },
  lime:    { bg: "bg-lime-500/[6%]",    bgActive: "bg-lime-500/15",    border: "border-lime-500/30",    text: "text-zinc-400", textActive: "text-lime-200",    iconBg: "bg-white/[5%]", iconBgActive: "bg-lime-500/20",    iconText: "text-lime-300",    iconTextActive: "text-lime-200" },
  yellow:  { bg: "bg-yellow-500/[6%]",  bgActive: "bg-yellow-500/15",  border: "border-yellow-500/30",  text: "text-zinc-400", textActive: "text-yellow-200",  iconBg: "bg-white/[5%]", iconBgActive: "bg-yellow-500/20",  iconText: "text-yellow-300",  iconTextActive: "text-yellow-200" },
  indigo:  { bg: "bg-indigo-500/[6%]",  bgActive: "bg-indigo-500/15",  border: "border-indigo-500/30",  text: "text-zinc-400", textActive: "text-indigo-200",  iconBg: "bg-white/[5%]", iconBgActive: "bg-indigo-500/20",  iconText: "text-indigo-300",  iconTextActive: "text-indigo-200" },
  zinc:    { bg: "bg-zinc-500/[6%]",    bgActive: "bg-zinc-500/15",    border: "border-zinc-500/30",    text: "text-zinc-400", textActive: "text-zinc-200",    iconBg: "bg-white/[5%]", iconBgActive: "bg-zinc-500/20",    iconText: "text-zinc-300",    iconTextActive: "text-zinc-200" },
  cyan:    { bg: "bg-cyan-500/[6%]",    bgActive: "bg-cyan-500/15",    border: "border-cyan-500/30",    text: "text-zinc-400", textActive: "text-cyan-200",    iconBg: "bg-white/[5%]", iconBgActive: "bg-cyan-500/20",    iconText: "text-cyan-300",    iconTextActive: "text-cyan-200" },
  orange:  { bg: "bg-orange-500/[6%]",  bgActive: "bg-orange-500/15",  border: "border-orange-500/30",  text: "text-zinc-400", textActive: "text-orange-200",  iconBg: "bg-white/[5%]", iconBgActive: "bg-orange-500/20",  iconText: "text-orange-300",  iconTextActive: "text-orange-200" },
}
