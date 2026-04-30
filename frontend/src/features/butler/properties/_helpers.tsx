/**
 * Common form helpers für die Butler-Property-Forms.
 *
 * Alle Forms greifen mit { params, onChange } darauf zu. Ein Single-Field-
 * Update sieht damit z.B. so aus:
 *   <TextInput label={t("labelKeyword")} field="keyword" params={p} onChange={onChange} />
 */
import type { ReactNode } from "react"

export type Params = Record<string, unknown>

export interface FormProps {
  params: Params
  onChange: (p: Params) => void
  agents?: { id: string; name: string }[]
}

const INPUT_CLS =
  "w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <div>
      <label className="block text-xs text-white/50 mb-1">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-white/25 mt-1">{hint}</p>}
    </div>
  )
}

export function TextInput({
  field, params, onChange, placeholder, mono, type = "text",
}: FormProps & { field: string; placeholder?: string; mono?: boolean; type?: string }) {
  return (
    <input
      type={type}
      placeholder={placeholder}
      value={(params[field] as string) || ""}
      onChange={e => onChange({ ...params, [field]: e.target.value })}
      className={mono ? `${INPUT_CLS} font-mono` : INPUT_CLS}
    />
  )
}

export function TextArea({
  field, params, onChange, placeholder, rows = 3, mono,
}: FormProps & { field: string; placeholder?: string; rows?: number; mono?: boolean }) {
  return (
    <textarea
      rows={rows}
      placeholder={placeholder}
      value={(params[field] as string) || ""}
      onChange={e => onChange({ ...params, [field]: e.target.value })}
      className={`${INPUT_CLS} resize-none ${mono ? "font-mono text-xs" : ""}`}
    />
  )
}

export function Select({
  field, params, onChange, options, defaultValue,
}: FormProps & { field: string; options: { value: string; label: string }[]; defaultValue?: string }) {
  return (
    <select
      value={(params[field] as string) || defaultValue || ""}
      onChange={e => onChange({ ...params, [field]: e.target.value })}
      className={INPUT_CLS}
    >
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  )
}

export function AgentSelect({
  field, params, onChange, agents, placeholder, allowAll,
}: FormProps & { field: string; placeholder: string; allowAll?: boolean }) {
  const items = agents || []
  return (
    <select
      value={(params[field] as string) || (allowAll ? "all" : "")}
      onChange={e => onChange({ ...params, [field]: e.target.value })}
      className={INPUT_CLS}
    >
      <option value={allowAll ? "all" : ""}>{placeholder}</option>
      {items.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
    </select>
  )
}

export function Info({ children }: { children: ReactNode }) {
  return <p className="text-xs text-white/35 leading-relaxed">{children}</p>
}
