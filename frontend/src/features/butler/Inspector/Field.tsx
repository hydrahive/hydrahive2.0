import type { ParamSchema } from "../types"

interface Props {
  schema: ParamSchema
  value: unknown
  onChange: (v: unknown) => void
}

const INPUT_CLS =
  "w-full px-2 py-1 text-xs bg-white/[3%] border border-white/[8%] rounded-md placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50"

export function Field({ schema, value, onChange }: Props) {
  const v = value ?? schema.default ?? ""

  return (
    <div className="space-y-1">
      <label className="text-[11px] text-zinc-400 flex items-center gap-1">
        {schema.label}
        {schema.required && <span className="text-rose-400">*</span>}
      </label>
      {render(schema, v, onChange)}
    </div>
  )
}

function render(schema: ParamSchema, v: unknown, onChange: (v: unknown) => void) {
  switch (schema.kind) {
    case "textarea":
    case "list_text":
      return (
        <textarea value={String(v)} rows={schema.kind === "textarea" ? 4 : 2}
          placeholder={schema.placeholder ?? ""}
          onChange={(e) => onChange(e.target.value)}
          className={`${INPUT_CLS} font-mono`} />
      )
    case "select":
      return (
        <select value={String(v)} onChange={(e) => onChange(e.target.value)}
          className={INPUT_CLS}>
          {schema.options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      )
    case "time":
      return (
        <input type="time" value={String(v)}
          onChange={(e) => onChange(e.target.value)} className={INPUT_CLS} />
      )
    case "number":
      return (
        <input type="number" value={String(v)}
          placeholder={schema.placeholder ?? ""}
          onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
          className={INPUT_CLS} />
      )
    case "checkbox":
      return (
        <input type="checkbox" checked={!!v}
          onChange={(e) => onChange(e.target.checked)}
          className="accent-violet-500" />
      )
    default:
      return (
        <input type="text" value={String(v)}
          placeholder={schema.placeholder ?? ""}
          onChange={(e) => onChange(e.target.value)}
          className={INPUT_CLS} />
      )
  }
}
