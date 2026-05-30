import { useEffect, useState } from "react"
import { akteApi, type AkteEntityKey, type AkteRecord } from "../api"
import { VerifyBadge } from "../components/VerifyBadge"
import { ResourceTable } from "../components/ResourceTable"

interface Column<T> {
  key: string
  label: string
  render?: (row: T) => React.ReactNode
}

const ENTITY_COLUMNS: Record<AkteEntityKey, Column<AkteRecord>[]> = {
  conditions: [
    { key: "label", label: "Diagnose", render: (r) => <span className="text-zinc-200">{r.label}</span> },
    { key: "icd_code", label: "ICD", render: (r) => <span className="text-zinc-500 font-mono text-xs">{(r.record as any).icd_code ?? "—"}</span> },
    { key: "status", label: "Status", render: (r) => <span className="text-zinc-400 text-xs">{(r.record as any).status ?? "—"}</span> },
    { key: "sort_date", label: "Datum", render: (r) => <span className="text-zinc-500 text-xs">{r.sort_date ? new Date(r.sort_date).toLocaleDateString("de-DE") : "—"}</span> },
    { key: "verifiziert", label: "✓", render: (r) => <VerifyBadge verifiziert={r.verifiziert} /> },
  ],
  medications: [
    { key: "label", label: "Medikament", render: (r) => <span className="text-zinc-200">{r.label}</span> },
    { key: "wirkstoff", label: "Wirkstoff", render: (r) => <span className="text-zinc-400 text-xs">{(r.record as any).wirkstoff ?? "—"}</span> },
    { key: "dosierung", label: "Dosierung", render: (r) => <span className="text-zinc-400 text-xs">{(r.record as any).dosierung ?? "—"}</span> },
    { key: "status", label: "Status", render: (r) => <span className="text-zinc-400 text-xs">{(r.record as any).status ?? "—"}</span> },
    { key: "sort_date", label: "Datum", render: (r) => <span className="text-zinc-500 text-xs">{r.sort_date ? new Date(r.sort_date).toLocaleDateString("de-DE") : "—"}</span> },
    { key: "verifiziert", label: "✓", render: (r) => <VerifyBadge verifiziert={r.verifiziert} /> },
  ],
  observations: [
    { key: "parameter", label: "Parameter", render: (r) => <span className="text-zinc-200">{(r.record as any).parameter ?? r.label}</span> },
    { key: "wert", label: "Wert", render: (r) => {
      const val = (r.record as any).wert
      const unit = (r.record as any).einheit ?? ""
      return val != null ? <span className="font-mono text-zinc-200">{val} {unit}</span> : <span className="text-zinc-500">{(r.record as any).wert_text ?? "—"}</span>
    }},
    { key: "sort_date", label: "Datum", render: (r) => <span className="text-zinc-500 text-xs">{r.sort_date ? new Date(r.sort_date).toLocaleDateString("de-DE") : "—"}</span> },
    { key: "verifiziert", label: "✓", render: (r) => <VerifyBadge verifiziert={r.verifiziert} /> },
  ],
  events: [
    { key: "label", label: "Ereignis", render: (r) => <span className="text-zinc-200">{r.label}</span> },
    { key: "typ", label: "Typ", render: (r) => <span className="text-zinc-400 text-xs">{(r.record as any).typ ?? "—"}</span> },
    { key: "sort_date", label: "Datum", render: (r) => <span className="text-zinc-500 text-xs">{r.sort_date ? new Date(r.sort_date).toLocaleDateString("de-DE") : "—"}</span> },
    { key: "verifiziert", label: "✓", render: (r) => <VerifyBadge verifiziert={r.verifiziert} /> },
  ],
  imaging: [
    { key: "label", label: "Befund", render: (r) => <span className="text-zinc-200">{r.label}</span> },
    { key: "körperstelle", label: "Körperstelle", render: (r) => <span className="text-zinc-400 text-xs">{(r.record as any).körperstelle ?? "—"}</span> },
    { key: "sort_date", label: "Datum", render: (r) => <span className="text-zinc-500 text-xs">{r.sort_date ? new Date(r.sort_date).toLocaleDateString("de-DE") : "—"}</span> },
    { key: "verifiziert", label: "✓", render: (r) => <VerifyBadge verifiziert={r.verifiziert} /> },
  ],
  allergies: [
    { key: "label", label: "Allergen", render: (r) => <span className="text-zinc-200">{r.label}</span> },
    { key: "reaktion", label: "Reaktion", render: (r) => <span className="text-zinc-400 text-xs">{(r.record as any).reaktion ?? "—"}</span> },
    { key: "sicherheit", label: "Sicherheit", render: (r) => <span className="text-zinc-500 text-xs">{(r.record as any).sicherheit ?? "—"}</span> },
    { key: "sort_date", label: "Datum", render: (r) => <span className="text-zinc-500 text-xs">{r.sort_date ? new Date(r.sort_date).toLocaleDateString("de-DE") : "—"}</span> },
    { key: "verifiziert", label: "✓", render: (r) => <VerifyBadge verifiziert={r.verifiziert} /> },
  ],
  practitioners: [
    { key: "name", label: "Name", render: (r) => <span className="text-zinc-200">{r.label}</span> },
    { key: "fachgebiet", label: "Fachgebiet", render: (r) => <span className="text-zinc-400 text-xs">{(r.record as any).fachgebiet ?? "—"}</span> },
    { key: "kontakt", label: "Kontakt", render: (r) => <span className="text-zinc-500 text-xs">{(r.record as any).kontakt ?? "—"}</span> },
    { key: "sort_date", label: "Seit", render: (r) => <span className="text-zinc-500 text-xs">{r.sort_date ? new Date(r.sort_date).toLocaleDateString("de-DE") : "—"}</span> },
    { key: "verifiziert", label: "✓", render: (r) => <VerifyBadge verifiziert={r.verifiziert} /> },
  ],
  documents: [
    { key: "label", label: "Dokument", render: (r) => <span className="text-zinc-200">{r.label}</span> },
    { key: "typ", label: "Typ", render: (r) => <span className="text-zinc-500 text-xs">{(r.record as any).typ ?? "—"}</span> },
    { key: "sort_date", label: "Datum", render: (r) => <span className="text-zinc-500 text-xs">{r.sort_date ? new Date(r.sort_date).toLocaleDateString("de-DE") : "—"}</span> },
    { key: "verifiziert", label: "✓", render: (r) => <VerifyBadge verifiziert={r.verifiziert} /> },
  ],
  notes: [
    { key: "label", label: "Titel", render: (r) => <span className="text-zinc-200">{r.label}</span> },
    { key: "notiz", label: "Inhalt", render: (r) => <span className="text-zinc-400 text-xs truncate max-w-xs">{(r.record as any).notiz ?? "—"}</span> },
    { key: "sort_date", label: "Datum", render: (r) => <span className="text-zinc-500 text-xs">{r.sort_date ? new Date(r.sort_date).toLocaleDateString("de-DE") : "—"}</span> },
    { key: "verifiziert", label: "✓", render: (r) => <VerifyBadge verifiziert={r.verifiziert} /> },
  ],
}

const ENTITY_LABELS: Record<AkteEntityKey, string> = {
  conditions:    "Diagnosen",
  medications:   "Medikamente",
  observations: "Laborwerte",
  events:        "Ereignisse",
  imaging:       "Bildgebung",
  allergies:     "Allergien",
  practitioners: "Ärzte",
  documents:     "Dokumente",
  notes:         "Notizen",
}

interface Props {
  entity: AkteEntityKey
  statusFilter?: string
}

export function AkteEntityList({ entity, statusFilter }: Props) {
  const [rows, setRows] = useState<AkteRecord[] | null>(null)
  const [search, setSearch] = useState("")
  const [deleting, setDeleting] = useState<string | null>(null)

  const load = () => {
    akteApi.listEntity(entity, { q: search || undefined, status: statusFilter })
      .then(setRows)
      .catch(() => setRows([]))
  }

  useEffect(() => { load() }, [entity, search, statusFilter])

  const handleVerify = async (eid: string) => {
    await akteApi.verifyEntity(entity, eid)
    setRows((prev) => prev?.map((r) => r.id === eid ? { ...r, verifiziert: 1 } : r) ?? null)
  }

  const handleDelete = async (eid: string) => {
    if (!confirm("Eintrag wirklich löschen?")) return
    setDeleting(eid)
    try {
      await akteApi.deleteEntity(entity, eid)
      setRows((prev) => prev?.filter((r) => r.id !== eid) ?? null)
    } finally {
      setDeleting(null)
    }
  }

  const handleVerifyBadge = (verifiziert: number, eid: string) => {
    if (verifiziert) return <VerifyBadge verifiziert={verifiziert} />
    return (
      <button
        onClick={() => handleVerify(eid)}
        className="text-orange-400 cursor-pointer hover:text-orange-300"
        title="Zum Verifizieren klicken"
      >
        ●
      </button>
    )
  }

  if (rows === null) {
    return <div className="h-48 rounded-xl bg-zinc-900/50 animate-pulse" />
  }

  const columns = ENTITY_COLUMNS[entity]
  const label = ENTITY_LABELS[entity]

  // Add action column
  const actionColumn: Column<AkteRecord> = {
    key: "_actions",
    label: "",
    render: (r) => (
      <div className="flex items-center gap-2">
        {handleVerifyBadge(r.verifiziert, r.id)}
        <button
          onClick={() => handleDelete(r.id)}
          disabled={deleting === r.id}
          className="text-zinc-600 hover:text-red-400 text-xs transition-colors disabled:opacity-50"
          title="Löschen"
        >
          ✕
        </button>
      </div>
    ),
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-base font-semibold text-zinc-100">{label}</h2>
        <span className="text-xs text-zinc-600">({rows.length})</span>
        <input
          type="search"
          placeholder="Suchen…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="ml-auto rounded-lg border border-white/[8%] bg-zinc-800 px-3 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 w-48"
        />
      </div>
      <ResourceTable
        rows={rows}
        columns={[...columns.slice(0, -1), actionColumn]}
        emptyText={`Keine ${label} vorhanden`}
      />
    </div>
  )
}