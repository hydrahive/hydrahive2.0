import { useEffect, useState } from "react"
import { Hash, Loader2, MessagesSquare, Megaphone, RefreshCw, ShieldCheck } from "lucide-react"
import { useTranslation } from "react-i18next"
import { communicationApi, type DiscordCatalogChannel } from "./api"

interface Props {
  value: string[]
  /** Teilmenge von value, in der die Moderations-Tools wirken dürfen. */
  moderated: string[]
  onChange: (ids: string[], moderated: string[]) => void
}

const KIND_ICON = { text: Hash, news: Megaphone, forum: MessagesSquare } as const

/** Freigabe der Kanäle für Agenten-Tools (discord_*). Leer = kein Zugriff. */
export function DiscordToolChannels({ value, moderated, onChange }: Props) {
  const { t } = useTranslation("communication")
  const [channels, setChannels] = useState<DiscordCatalogChannel[]>([])
  const [connected, setConnected] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let alive = true
    communicationApi.discord.channels()
      .then((res) => { if (alive) { setConnected(res.connected); setChannels(res.channels) } })
      .catch(() => { if (alive) setConnected(false) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [reloadKey])

  function reload() {
    setLoading(true)
    setReloadKey((k) => k + 1)
  }

  const selected = new Set(value)
  const mod = new Set(moderated.filter((id) => selected.has(id)))
  const known = new Set(channels.map((c) => c.id))
  const orphaned = value.filter((id) => !known.has(id))

  // Abwählen eines Kanals entzieht auch die Moderation — sie setzt Zugriff voraus.
  function toggle(id: string) {
    const next = new Set(selected)
    const nextMod = new Set(mod)
    if (next.has(id)) { next.delete(id); nextMod.delete(id) }
    else next.add(id)
    onChange(Array.from(next), Array.from(nextMod))
  }

  function toggleMod(id: string) {
    const nextMod = new Set(mod)
    if (nextMod.has(id)) nextMod.delete(id)
    else nextMod.add(id)
    onChange(Array.from(selected), Array.from(nextMod))
  }

  const groups = new Map<string, DiscordCatalogChannel[]>()
  for (const c of channels) {
    const key = c.category ? `${c.guild} · ${c.category}` : c.guild
    groups.set(key, [...(groups.get(key) ?? []), c])
  }

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <label className="text-xs text-zinc-400">{t("discord.tools.label")}</label>
        <button type="button" onClick={reload} disabled={loading}
          className="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-300 disabled:opacity-40">
          {loading ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />}
          {t("discord.tools.reload")}
        </button>
      </div>
      <p className="text-[10px] text-zinc-600">{t("discord.tools.hint")}</p>

      <div className="max-h-56 overflow-y-auto rounded-md border border-white/[8%] bg-white/[2%] p-2 space-y-2">
        {connected === false && (
          <p className="text-[11px] text-amber-300/80">{t("discord.tools.not_connected")}</p>
        )}
        {connected && channels.length === 0 && (
          <p className="text-[11px] text-zinc-500">{t("discord.tools.no_channels")}</p>
        )}
        {Array.from(groups.entries()).map(([group, items]) => (
          <div key={group} className="space-y-0.5">
            <p className="text-[10px] uppercase tracking-wide text-zinc-600">{group}</p>
            {items.map((c) => {
              const Icon = KIND_ICON[c.kind]
              return (
                <label key={c.id} className="flex items-center gap-2 cursor-pointer rounded px-1 py-0.5 hover:bg-white/[4%]">
                  <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggle(c.id)}
                    className="accent-[var(--hh-accent-from)] w-3.5 h-3.5" />
                  <Icon size={12} className="text-zinc-500 shrink-0" />
                  <span className="text-xs text-zinc-200 truncate">{c.name}</span>
                  {c.kind === "forum" && <span className="text-[10px] text-violet-300/70">{t("discord.tools.forum")}</span>}
                  {!c.can_send && <span className="text-[10px] text-zinc-500">{t("discord.tools.read_only")}</span>}
                  {selected.has(c.id) && (
                    <button type="button" onClick={(e) => { e.preventDefault(); toggleMod(c.id) }}
                      title={t("discord.tools.moderate_hint")}
                      className={`ml-auto flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-[10px] ${mod.has(c.id) ? "bg-amber-400/15 text-amber-200" : "text-zinc-500 hover:text-zinc-300"}`}>
                      <ShieldCheck size={11} />{t("discord.tools.moderate")}
                    </button>
                  )}
                </label>
              )
            })}
          </div>
        ))}
        {orphaned.map((id) => (
          <label key={id} className="flex items-center gap-2 cursor-pointer rounded px-1 py-0.5 hover:bg-white/[4%]">
            <input type="checkbox" checked onChange={() => toggle(id)}
              className="accent-[var(--hh-accent-from)] w-3.5 h-3.5" />
            <span className="text-xs font-mono text-zinc-400">{id}</span>
            <span className="text-[10px] text-amber-300/70">{t("discord.tools.unreachable")}</span>
          </label>
        ))}
      </div>
      <p className="text-[10px] text-zinc-500">
        {value.length === 0 ? t("discord.tools.none_selected") : t("discord.tools.count", { count: value.length })}
        {mod.size > 0 && ` ${t("discord.tools.moderated_count", { count: mod.size })}`}
      </p>
    </div>
  )
}
