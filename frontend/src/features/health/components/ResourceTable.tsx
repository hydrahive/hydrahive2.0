import { useTranslation } from "react-i18next"
import type { CSSProperties } from "react"
import { rgbFor } from "@/shared/colors"

interface Column<T> {
  key: string
  label: string
  render?: (row: T) => React.ReactNode
}

interface Props<T> {
  rows: T[]
  columns: Column<T>[]
  emptyText?: string
}

export function ResourceTable<T extends Record<string, unknown>>({ rows, columns, emptyText }: Props<T>) {
  const { t } = useTranslation("health")
  const empty = emptyText ?? t("akte.no_entries")
  if (rows.length === 0) {
    return <p className="text-sm text-zinc-500 py-8 text-center">{empty}</p>
  }
  return (
    <div className="box overflow-hidden" style={{ "--c": rgbFor("/health") } as CSSProperties}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/[6%] bg-zinc-900/50">
            {columns.map((col) => (
              <th key={col.key} className="px-4 py-2 text-left text-xs font-medium text-zinc-500 uppercase tracking-wider">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={String(row.id ?? i)} className="border-b border-white/[4%] hover:bg-white/[2%] transition-colors">
              {columns.map((col) => (
                <td key={col.key} className="px-4 py-3 text-zinc-300">
                  {col.render ? col.render(row) : String(row[col.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
