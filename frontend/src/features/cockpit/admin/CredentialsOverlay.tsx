import { useEffect, useState } from "react"
import { Key, Loader2, Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { credentialsApi } from "@/features/credentials/api"
import { CredentialEditor } from "@/features/credentials/CredentialEditor"
import { ExtensionCredentials } from "@/features/credentials/ExtensionCredentials"
import type { Credential } from "@/features/credentials/types"
import { countUnbound } from "@/features/credentials/unbound"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"
import { CredentialCockpitCard, UnboundBanner } from "./CredentialCockpitCard"
import { ADMIN_OVERLAY_THEME } from "@/shared/brand/boxThemes"

type Tab = "http" | "extensions"

export function CredentialsOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("credentials")
  const role = useAuthStore((s) => s.role)
  const [tab, setTab] = useState<Tab>("http")
  const [creds, setCreds] = useState<Credential[]>([])
  const [loading, setLoading] = useState(true)
  const [editor, setEditor] = useState<Credential | "new" | null>(null)

  async function reload() {
    setLoading(true)
    try { setCreds(await credentialsApi.list()) } catch { setCreds([]) } finally { setLoading(false) }
  }
  useEffect(() => { reload() }, [])

  return (
    <AdminOverlay theme={ADMIN_OVERLAY_THEME["credentials"]}
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      maxWidthClass="max-w-4xl"
      headerActions={tab === "http" ? (
        <CockpitButton tone="primary" onClick={() => setEditor("new")}>
          <Plus size={12} className="mr-1 inline" />{t("new")}
        </CockpitButton>
      ) : undefined}
    >
      <div className="space-y-4">
        <p className="text-sm text-[#9aa7bc]">{t("subtitle")}</p>

        <div className="flex gap-2 border-b border-s-rand">
          <button onClick={() => setTab("http")}
            className={`-mb-px flex items-center gap-1.5 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              tab === "http" ? "border-violet-500 text-violet-300" : "border-transparent text-[#9aa7bc] hover:text-[#e8eef8]"
            }`}>
            <Key size={13} /> HTTP-Credentials
          </button>
          {role === "admin" && (
            <button onClick={() => setTab("extensions")}
              className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                tab === "extensions" ? "border-violet-500 text-violet-300" : "border-transparent text-[#9aa7bc] hover:text-[#e8eef8]"
              }`}>
              Extensions
            </button>
          )}
        </div>

        {tab === "extensions" && <ExtensionCredentials />}

        {tab === "http" && (
          <>
            <p className="rounded-[4px] border border-amber-500/15 bg-amber-500/[5%] px-3 py-2 text-[11px] text-amber-200/90">
              {t("security_note")}
            </p>

            <UnboundBanner count={countUnbound(creds)} />

            {loading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 size={20} className="animate-spin text-[#9aa7bc]" />
              </div>
            ) : creds.length === 0 ? (
              <p className="py-8 text-center text-xs text-[#9aa7bc]">{t("empty")}</p>
            ) : (
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                {creds.map((c) => <CredentialCockpitCard key={c.name} credential={c} onOpen={() => setEditor(c)} />)}
              </div>
            )}
          </>
        )}
      </div>

      {tab === "http" && editor && (
        <CredentialEditor
          credential={editor === "new" ? null : editor}
          onClose={() => setEditor(null)}
          onSaved={async () => { setEditor(null); await reload() }}
          onDeleted={async () => { setEditor(null); await reload() }}
        />
      )}
    </AdminOverlay>
  )
}
