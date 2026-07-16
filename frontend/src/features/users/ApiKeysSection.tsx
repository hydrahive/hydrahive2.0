import { useCallback, useEffect, useState } from "react"
import { Copy, KeyRound, Plus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import {
  AdminAction,
  AdminCodeBlock,
  AdminConfirmDialog,
  AdminFeedback,
  AdminPanel,
  adminInputClass,
} from "@/features/cockpit/admin/ui"
import { apiKeysApi } from "./api"
import type { ApiKey } from "./types"

export function ApiKeysSection() {
  const { t } = useTranslation("users")
  const { t: tCommon } = useTranslation("common")
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [loading, setLoading] = useState(true)
  const [newName, setNewName] = useState("")
  const [creating, setCreating] = useState(false)
  const [newKey, setNewKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<ApiKey | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setKeys(await apiKeysApi.list())
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : tCommon("status.error"))
    } finally {
      setLoading(false)
    }
  }, [tCommon])

  useEffect(() => {
    const initial = window.setTimeout(load, 0)
    return () => window.clearTimeout(initial)
  }, [load])

  async function handleCreate() {
    if (creating || !newName.trim()) return
    setCreating(true)
    setError(null)
    try {
      const result = await apiKeysApi.create(newName.trim())
      setNewKey(result.key)
      setNewName("")
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : tCommon("status.error"))
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    setError(null)
    try {
      await apiKeysApi.delete(deleteTarget.id)
      setDeleteTarget(null)
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : tCommon("status.error"))
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  async function handleCopy() {
    if (!newKey) return
    try {
      await navigator.clipboard.writeText(newKey)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : tCommon("status.error"))
    }
  }

  return (
    <>
      <AdminPanel title={t("apikeys.title")} description={t("apikeys.subtitle")} icon={KeyRound} bodyClassName="space-y-4">
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
        {loading && <AdminFeedback loading>API-Keys werden geladen …</AdminFeedback>}

        {newKey && (
          <div className="space-y-3 rounded-[6px] border border-amber-500/25 bg-amber-500/[7%] p-3">
            <AdminFeedback tone="warning">{t("apikeys.save_now")}</AdminFeedback>
            <div className="flex items-start gap-2">
              <AdminCodeBlock className="min-w-0 flex-1 break-all">{newKey}</AdminCodeBlock>
              <AdminAction onClick={handleCopy} className="shrink-0 px-2" title={t("apikeys.copy")} aria-label={t("apikeys.copy")}>
                <Copy size={14} />
              </AdminAction>
            </div>
            {copied && <AdminFeedback tone="success">{t("apikeys.copied")}</AdminFeedback>}
            <AdminAction tone="ghost" onClick={() => { setNewKey(null); setCopied(false) }}>{t("apikeys.dismiss")}</AdminAction>
          </div>
        )}

        <div className="flex gap-2">
          <input
            type="text"
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Enter" && !creating) handleCreate() }}
            placeholder={t("apikeys.name_placeholder")}
            className={`${adminInputClass} flex-1`}
          />
          <AdminAction tone="primary" onClick={handleCreate} disabled={creating || !newName.trim()}>
            <Plus size={14} />{t("apikeys.create")}
          </AdminAction>
        </div>

        {keys.length > 0 ? (
          <div className="space-y-1.5">
            {keys.map((key) => (
              <div key={key.id} className="flex items-center gap-3 rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-3 py-2">
                <KeyRound size={13} className="shrink-0 text-[#69d7ff]" />
                <div className="min-w-0 flex-1">
                  <span className="text-sm text-[#e8eef8]">{key.name}</span>
                  <span className="ml-2 text-xs text-[#5b6675]">{key.username}</span>
                </div>
                <span className="shrink-0 text-xs text-[#5b6675]">{new Date(key.created_at).toLocaleDateString()}</span>
                <AdminAction tone="danger" className="shrink-0 px-2" onClick={() => setDeleteTarget(key)} title={t("actions.delete")} aria-label={t("actions.delete")}>
                  <Trash2 size={13} />
                </AdminAction>
              </div>
            ))}
          </div>
        ) : !loading && !newKey ? <p className="text-xs italic text-[#5b6675]">{t("apikeys.empty")}</p> : null}
      </AdminPanel>

      {deleteTarget && (
        <AdminConfirmDialog
          title={t("actions.delete")}
          confirmLabel={t("actions.delete")}
          cancelLabel={tCommon("actions.cancel")}
          onConfirm={handleDelete}
          onClose={() => setDeleteTarget(null)}
          busy={deleting}
        >
          {t("apikeys.delete_confirm")}
        </AdminConfirmDialog>
      )}
    </>
  )
}
