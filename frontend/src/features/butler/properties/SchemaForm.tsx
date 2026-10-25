/**
 * Eingabeformular für Butler-Bausteine aus Modulen – gebaut aus dem ParamSchema des Servers
 * (docs/specs/butler-module-nodes.md §2). Eingebaute Bausteine behalten ihre eigenen Formulare.
 */
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { cleanSchemaValue, type ModuleNode, type SchemaParam } from "../moduleNodes"
import { Field, Info, type Params } from "./_helpers"

const INPUT_CLS =
  "w-full rounded-lg bg-zinc-900 border border-white/15 px-2 py-1.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-white/30"

/** Liste, eine Angabe je Zeile: Rohtext lokal halten (leere Zeile beim Tippen bleibt), gespeichert wird die Liste. */
function ListInput({ value, set, placeholder }: { value: unknown; set: (v: unknown) => void; placeholder?: string }) {
  const [text, setText] = useState(Array.isArray(value) ? value.join("\n") : "")
  return <textarea rows={3} placeholder={placeholder} value={text}
    onChange={(e) => { setText(e.target.value); set(e.target.value) }}
    className={`${INPUT_CLS} resize-none font-mono text-xs`} />
}

function Input({ p, value, set }: { p: SchemaParam; value: unknown; set: (v: unknown) => void }) {
  const { t } = useTranslation("butler")
  const ph = p.placeholder ?? undefined
  switch (p.kind) {
    case "textarea":
      return <textarea rows={3} placeholder={ph} value={(value as string) ?? ""} onChange={(e) => set(e.target.value)}
        className={`${INPUT_CLS} resize-none`} />
    case "list_text":
      return <ListInput placeholder={ph} value={value} set={set} />
    case "select":
      return (
        <select value={(value as string) ?? ""} onChange={(e) => set(e.target.value)} className={INPUT_CLS}>
          {!p.required && <option value="">{t("schemaNone")}</option>}
          {p.options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      )
    case "number":
      return <input type="number" placeholder={ph} value={value === undefined || value === null ? "" : String(value)}
        onChange={(e) => set(e.target.value)} className={INPUT_CLS} />
    case "checkbox":
      return <input type="checkbox" checked={value === true} onChange={(e) => set(e.target.checked)}
        className="h-4 w-4 accent-orange-500" />
    case "time":
      return <input type="time" value={(value as string) ?? ""} onChange={(e) => set(e.target.value)} className={INPUT_CLS} />
    default:
      return <input type="text" placeholder={ph} value={(value as string) ?? ""} onChange={(e) => set(e.target.value)}
        className={INPUT_CLS} />
  }
}

export function SchemaForm({ node, params, onChange }: { node: ModuleNode; params: Params; onChange: (p: Params) => void }) {
  const { t } = useTranslation("butler")
  const set = (p: SchemaParam) => (raw: unknown) => {
    const v = cleanSchemaValue(p, raw)
    const next = { ...params }
    if (v === undefined) delete next[p.key]
    else next[p.key] = v
    onChange(next)
  }
  return (
    <div className="flex flex-col gap-3" data-butler-schema-form={node.subtype}>
      {node.description && <Info>{node.description}</Info>}
      {node.params.map((p) => (
        <Field key={p.key} label={p.required ? `${p.label} *` : p.label}
          hint={p.kind === "list_text" ? t("schemaListHint") : undefined}>
          <Input p={p} value={params[p.key]} set={set(p)} />
        </Field>
      ))}
      <p className="text-[10px] text-white/30">{t("schemaFromModule", { module: node.module })}</p>
    </div>
  )
}
