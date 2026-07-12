import { useEffect, useState } from "react"
import { Loader2, Network } from "lucide-react"
import type { Project } from "@/features/projects/types"
import { codeGraphApi, graphFileUrl, type CodeGraphStatus } from "../codeGraphApi"
import { CockpitButton } from "../CockpitButton"
import { CockpitSectionLabel } from "../CockpitPanel"

export function ProjectGraphOverlay({ project, onClose }: { project: Project; onClose: () => void }) {
  const [status, setStatus] = useState<CodeGraphStatus | null>(null)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [building, setBuilding] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    Promise.all([codeGraphApi.status(project.id), codeGraphApi.getConfig(project.id)])
      .then(([st, cfg]) => {
        if (!alive) return
        setStatus(st)
        // Vorschläge + bereits gewählte Verzeichnisse zusammenführen.
        setSuggestions(Array.from(new Set([...cfg.suggestions, ...cfg.scan_dirs])))
        setSelected(cfg.scan_dirs.length ? cfg.scan_dirs : cfg.suggestions.slice(0, 3))
      })
      .catch(() => { if (alive) setError("Status konnte nicht geladen werden.") })
    return () => { alive = false }
  }, [project.id])

  const toggle = (dir: string) => {
    setSelected((cur) => (cur.includes(dir) ? cur.filter((d) => d !== dir) : [...cur, dir]))
  }

  const runBuild = async () => {
    setBuilding(true)
    setError(null)
    try {
      await codeGraphApi.setConfig(project.id, selected)
      const result = await codeGraphApi.build(project.id)
      setStatus((cur) => ({ ...(cur as CodeGraphStatus), ...result, installed: true }))
    } catch (err) {
      setError(err instanceof Error ? err.message : "Graph-Build fehlgeschlagen.")
    } finally {
      setBuilding(false)
    }
  }

  const htmlUrl = status?.html_path ? graphFileUrl(status.html_path) : null
  const metrics = status?.metrics
  const god = status?.report?.god_nodes ?? []
  const cycles = status?.report?.cycles ?? []

  return (
    <div className="fixed inset-0 z-[100] grid place-items-center bg-black/80 p-4" role="dialog" aria-modal="true" aria-labelledby="project-graph-title">
      <section className="flex h-[min(880px,95dvh)] w-full max-w-6xl flex-col overflow-hidden rounded-[6px] border border-[#46617f] bg-[#151c2b] shadow-2xl">
        <header className="flex items-center justify-between border-b border-[#2a364b] p-4">
          <div>
            <CockpitSectionLabel>Codebase-Analyse</CockpitSectionLabel>
            <h2 id="project-graph-title" className="mt-1 flex items-center gap-2 text-lg font-semibold text-[#e8eef8]">
              <Network size={18} /> Code-Graph
            </h2>
            <p className="mt-1 text-xs text-[#8d9ab0]">{project.name} · lokal, ohne LLM</p>
          </div>
          <CockpitButton onClick={onClose}>Schließen</CockpitButton>
        </header>

        <main className="grid min-h-0 flex-1 gap-3 overflow-y-auto p-4 lg:grid-cols-[280px_1fr]">
          {/* Steuerung: Verzeichnis-Auswahl + Build */}
          <div className="space-y-3">
            <div className="rounded-[4px] border border-[#2a364b] bg-[#101724] p-3">
              <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-[#68758a]">Verzeichnisse</p>
              {suggestions.length === 0 ? (
                <p className="text-xs text-[#7a869c]">Keine Quellordner gefunden.</p>
              ) : (
                <ul className="space-y-1">
                  {suggestions.map((dir) => (
                    <li key={dir}>
                      <label className="flex cursor-pointer items-center gap-2 text-xs text-[#c3ccdd]">
                        <input type="checkbox" checked={selected.includes(dir)} onChange={() => toggle(dir)} className="accent-cyan-400" />
                        <span className="truncate font-mono">{dir}</span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
              <button
                type="button"
                onClick={runBuild}
                disabled={building || selected.length === 0}
                className="mt-3 inline-flex w-full items-center justify-center gap-1.5 rounded-[4px] border border-cyan-400/50 bg-cyan-400/10 px-3 py-1.5 text-[12px] font-semibold text-cyan-100 transition-colors hover:bg-cyan-400/20 disabled:opacity-40"
              >
                {building ? <Loader2 size={14} className="animate-spin" /> : <Network size={14} />}
                {building ? "Baue Graph…" : "Graph bauen"}
              </button>
              {building ? <p className="mt-2 text-[11px] text-[#8d9ab0]">Erstlauf richtet das Analyse-Tool ein — kann einen Moment dauern.</p> : null}
              {error ? <p className="mt-2 text-[11px] text-rose-300">{error}</p> : null}
            </div>

            {metrics?.nodes ? (
              <div className="rounded-[4px] border border-[#2a364b] bg-[#101724] p-3 text-xs text-[#c3ccdd]">
                <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-[#68758a]">Kennzahlen</p>
                <p>{metrics.nodes} Knoten · {metrics.edges} Kanten · {metrics.communities} Communities</p>
                {status?.built_at ? <p className="mt-1 text-[10px] text-[#68758a]">Stand: {new Date(status.built_at).toLocaleString()}</p> : null}
              </div>
            ) : null}

            {god.length ? (
              <div className="rounded-[4px] border border-[#2a364b] bg-[#101724] p-3">
                <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-[#68758a]">Zentrale Knoten</p>
                <ul className="space-y-0.5 text-xs text-[#c3ccdd]">
                  {god.map((g) => (
                    <li key={g.name} className="flex justify-between gap-2">
                      <span className="truncate font-mono">{g.name}</span>
                      <span className="text-[#68758a]">{g.edges}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {cycles.length ? (
              <div className="rounded-[4px] border border-rose-500/30 bg-rose-500/5 p-3">
                <p className="mb-1 font-mono text-[10px] uppercase tracking-[0.14em] text-rose-300">Import-Zyklen</p>
                <ul className="space-y-1 text-[11px] text-rose-200">
                  {cycles.map((c) => <li key={c} className="break-all font-mono leading-snug">{c}</li>)}
                </ul>
              </div>
            ) : metrics ? (
              <div className="rounded-[4px] border border-emerald-500/25 bg-emerald-500/5 p-3">
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-emerald-300">Import-Zyklen</p>
                <p className="mt-1 text-[11px] text-emerald-200/90">Keine echten Zyklen gefunden.</p>
              </div>
            ) : null}
          </div>

          {/* Interaktiver Graph */}
          <div className="min-h-[400px] overflow-hidden rounded-[4px] border border-[#2a364b] bg-[#0d1420]">
            {htmlUrl ? (
              <iframe src={htmlUrl} title="Code-Graph" className="h-full min-h-[400px] w-full border-0" />
            ) : (
              <div className="grid h-full min-h-[400px] place-items-center text-center text-sm text-[#7a869c]">
                <div>
                  <Network size={32} className="mx-auto mb-2 text-[#3f4b60]" />
                  <p>Noch kein Graph gebaut.</p>
                  <p className="mt-1 text-xs">Verzeichnisse wählen und „Graph bauen".</p>
                </div>
              </div>
            )}
          </div>
        </main>

        <footer className="border-t border-[#2a364b] p-3 text-xs text-[#8d9ab0]">
          Code-Graph läuft komplett lokal (tree-sitter AST) — keine API-Kosten, kein Datenabfluss.
        </footer>
      </section>
    </div>
  )
}
