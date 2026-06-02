interface Props {
  src: string
  title?: string
  hint?: React.ReactNode
  size?: number
  className?: string
  children?: React.ReactNode
}

export function EmptyState({ src, title, hint, size = 112, className = "", children }: Props) {
  return (
    <div className={`flex flex-col items-center justify-center text-center gap-2.5 py-8 px-6 ${className}`}>
      <img
        src={src}
        alt=""
        width={size}
        height={size}
        className="object-contain opacity-95 drop-shadow-[0_0_20px_rgba(34,211,238,0.22)] select-none pointer-events-none"
      />
      {title && <p className="text-sm font-medium text-zinc-300">{title}</p>}
      {hint && <p className="text-xs text-zinc-500 max-w-[22rem] leading-relaxed">{hint}</p>}
      {children}
    </div>
  )
}
