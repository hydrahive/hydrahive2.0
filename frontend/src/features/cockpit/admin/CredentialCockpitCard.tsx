import { AlertTriangle, Key } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Credential } from "@/features/credentials/types"

/** Warnung über Zugänge ohne Host (gleiche Aussage wie im Einstellungs-Hub). */
export function UnboundBanner({ count }: { count: number }) {
  const { t } = useTranslation("credentials")
  if (count <= 0) return null
  return (
    <p className="flex items-start gap-2 rounded-[4px] border border-amber-500/30 bg-amber-500/[8%] px-3 py-2 text-xs text-amber-200">
      <AlertTriangle size={13} className="mt-0.5 shrink-0" />
      {t("unbound_banner", { count })}
    </p>
  )
}

/** Karte eines HTTP-Zugangs im Admin-Fenster „Zugangsdaten“. */
export function CredentialCockpitCard({ credential: c, onOpen }: { credential: Credential; onOpen: () => void }) {
  const { t } = useTranslation("credentials")
  return (
    <button onClick={onOpen}
      className="rounded-[6px] border border-s-rand bg-s-innen p-3 text-left transition-colors hover:border-s-rand-hover hover:bg-s-hebung">
      <div className="mb-1 flex items-center gap-2">
        <Key size={11} className="shrink-0 text-amber-300" />
        <p className="flex-1 truncate font-mono text-sm text-[#e8eef8]">{c.name}</p>
        <span className="shrink-0 rounded-full border border-violet-500/20 bg-violet-500/[8%] px-1.5 py-0.5 text-[10px] text-violet-300">
          {t(`type_${c.type}`)}
        </span>
      </div>
      {c.description && <p className="line-clamp-1 text-xs text-[#9aa7bc]">{c.description}</p>}
      <p className="mt-1 truncate font-mono text-[10px] text-[#9aa7bc]">{c.url_pattern}</p>
      {c.host_bound === false && (
        <p className="mt-0.5 flex items-center gap-1 text-[10px] text-amber-300">
          <AlertTriangle size={10} /> {t("not_host_bound")}
        </p>
      )}
    </button>
  )
}
