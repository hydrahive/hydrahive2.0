import type { CSSProperties, HTMLAttributes, ReactNode } from "react"
import { cn } from "@/shared/cn"

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Domain-Farbe der Box als "r g b" (siehe shared/colors rgbFor). */
  color?: string
  /** Kein Hover-Lift (für interaktive Inhalte wie Terminals). */
  static?: boolean
  /** Innen-Padding aus. */
  flush?: boolean
  children?: ReactNode
}

export function Card({ color, static: isStatic, flush, className, style, children, ...rest }: CardProps) {
  const cssVars = color ? ({ "--c": color } as CSSProperties) : undefined
  return (
    <div
      {...rest}
      style={{ ...cssVars, ...style }}
      className={cn("box", isStatic && "box-static", !flush && "p-5", className)}
    >
      {children}
    </div>
  )
}

interface CardHeaderProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  icon?: ReactNode
  title: ReactNode
  right?: ReactNode
}

export function CardHeader({ icon, title, right, className, ...rest }: CardHeaderProps) {
  return (
    <div {...rest} className={cn("flex items-center gap-2 mb-3", className)}>
      {icon && <span className="text-[var(--hh-accent-text)] [&>svg]:block">{icon}</span>}
      <h3 className="text-sm font-semibold text-zinc-100">{title}</h3>
      {right && <div className="ml-auto">{right}</div>}
    </div>
  )
}
