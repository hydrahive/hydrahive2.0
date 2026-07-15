import { useEffect, useState } from "react"
import { Key, Loader2, Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { credentialsApi } from "@/features/credentials/api"
import { CredentialEditor } from "@/features/credentials/CredentialEditor"
import { ExtensionCredentials } from "@/features/credentials/ExtensionCredentials"
import type { Credential } from "@/features/credentials/types"
import { CockpitButton } from "../CockpitButton"
import { AdminOverlay } from "./AdminOverlay"

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
    <AdminOverlay
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
        <p className="text-sm text-[#8d9ab0]">{t("subtitle")}</p>

        <div className="flex gap-2 border-b border-[#2a364b]">
          <button onClick={() => setTab("http")}
            className={`-mb-px flex items-center gap-1.5 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              tab === "http" ? "border-violet-500 text-violet-300" : "border-transparent text-[#8d9ab0] hover:text-[#e8eef8]"
            }`}>
            <Key size={13} /> HTTP-Credentials
          </button>
          {role === "admin" && (
            <button onClick={() => setTab("extensions")}
              className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
                tab === "extensions" ? "border-violet-500 text-violet-300" : "border-transparent text-[#8d9ab0] hover:text-[#e8eef8]"
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

            {loading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 size={20} className="animate-spin text-[#8d9ab0]" />
              </div>
            ) : creds.length === 0 ? (
              <p className="py-8 text-center text-xs text-[#8d9ab0]">{t("empty")}</p>
            ) : (
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                {creds.map((c) => (
                  <button key={c.name} onClick={() => setEditor(c)}
                    className="rounded-[6px] border border-[#2a364b] bg-[#111827] p-3 text-left transition-colors hover:border-[#46617f] hover:bg-[#172133]">
                    <div className="mb-1 flex items-center gap-2">
                      <Key size={11} className="shrink-0 text-amber-300" />
                      <p className="flex-1 truncate font-mono text-sm text-[#e8eef8]">{c.name}</p>
                      <span className="shrink-0 rounded-full border border-violet-500/20 bg-violet-500/[8%] px-1.5 py-0.5 text-[10px] text-violet-300">
                        {t(`type_${c.type}`)}
                      </span>
                    </div>
                    {c.description && <p className="line-clamp-1 text-xs text-[#8d9ab0]">{c.description}</p>}
                    <p className="mt-1 truncate font-mono text-[10px] text-[#5b6675]">{c.url_pattern}</p>
                  </button>
                ))}
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
