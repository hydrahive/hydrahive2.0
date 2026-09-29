import { useCallback, useEffect, useState } from "react"
import { Plus, Trash2, Users, X } from "lucide-react"
import { useTranslation } from "react-i18next"
import { AdminAction, AdminConfirmDialog, AdminFeedback, AdminPanel, adminInputClass } from "@/features/cockpit/admin/ui"
import { accessApi } from "./api"
import type { AccessGroupDetail, AccessUser } from "./types"

export function GroupsSection({ users }: { users: AccessUser[] }) {
  const { t } = useTranslation("access")
  const { t: tCommon } = useTranslation("common")
  const [groups, setGroups] = useState<AccessGroupDetail[]>([])
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState("")
  const [pick, setPick] = useState<Record<string, string>>({})
  const [deleteTarget, setDeleteTarget] = useState<AccessGroupDetail | null>(null)

  const run = useCallback(async (fn: () => Promise<unknown>) => {
    try { await fn(); setError(null) } catch (e) { setError(e instanceof Error ? e.message : tCommon("status.error")) }
  }, [tCommon])

  const load = useCallback(() => run(async () => {
    const list = await accessApi.groups()
    setGroups(await Promise.all(list.map((g) => accessApi.group(g.id))))
  }), [run])

  useEffect(() => { const id = window.setTimeout(load, 0); return () => window.clearTimeout(id) }, [load])

  const create = () => run(async () => { await accessApi.createGroup(name.trim(), ""); setName(""); await load() })
  const addMember = (gid: string) => run(async () => {
    if (!pick[gid]) return
    await accessApi.addMember(gid, pick[gid]); setPick({ ...pick, [gid]: "" }); await load()
  })
  const removeMember = (gid: string, uid: string) => run(async () => { await accessApi.removeMember(gid, uid); await load() })
  const remove = () => run(async () => {
    if (deleteTarget) await accessApi.deleteGroup(deleteTarget.id)
    setDeleteTarget(null); await load()
  })

  return (
    <AdminPanel title={t("groups.title")} description={t("groups.description")} icon={Users}>
      <div className="space-y-3 p-4">
        {error && <AdminFeedback tone="danger">{error}</AdminFeedback>}
        <div className="flex gap-2">
          <input className={adminInputClass} value={name} placeholder={t("groups.name")} maxLength={80}
            onChange={(e) => setName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && name.trim()) create() }} />
          <AdminAction tone="primary" disabled={!name.trim()} onClick={create}>
            <Plus size={13} className="mr-1 inline" />{t("groups.create")}
          </AdminAction>
        </div>
        {groups.length === 0 && <AdminFeedback>{t("groups.empty")}</AdminFeedback>}
        {groups.map((g) => {
          const free = users.filter((u) => !g.members.some((m) => m.user_id === u.user_id))
          return (
            <div key={g.id} className="rounded-[6px] border border-[#2a364b] bg-[#0d1420] p-3">
              <div className="flex items-center gap-2">
                <p className="flex-1 text-sm font-bold text-[#e8eef8]">{g.name}</p>
                <span className="text-xs text-[#8d9ab0]">{t("groups.members_count", { count: g.members.length })}</span>
                <AdminAction tone="danger" className="px-2" title={t("groups.delete")} aria-label={t("groups.delete")}
                  onClick={() => setDeleteTarget(g)}><Trash2 size={13} /></AdminAction>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {g.members.length === 0 && <span className="text-xs text-[#5b6675]">{t("groups.no_members")}</span>}
                {g.members.map((m) => (
                  <span key={m.user_id} className="inline-flex items-center gap-1 rounded-full border border-[#2a364b] bg-[#172133] px-2 py-0.5 text-xs text-[#e8eef8]">
                    {m.username || m.user_id}
                    <button type="button" className="text-[#8d9ab0] hover:text-rose-300" title={t("groups.remove_member")}
                      aria-label={t("groups.remove_member")} onClick={() => removeMember(g.id, m.user_id)}><X size={11} /></button>
                  </span>
                ))}
              </div>
              {free.length > 0 && (
                <div className="mt-2 flex gap-2">
                  <select className={adminInputClass} value={pick[g.id] ?? ""} aria-label={t("groups.add_member")}
                    onChange={(e) => setPick({ ...pick, [g.id]: e.target.value })}>
                    <option value="">{t("groups.choose_user")}</option>
                    {free.map((u) => <option key={u.user_id} value={u.user_id}>{u.username}</option>)}
                  </select>
                  <AdminAction disabled={!pick[g.id]} onClick={() => addMember(g.id)}>{t("groups.add_member")}</AdminAction>
                </div>
              )}
            </div>
          )
        })}
      </div>
      {deleteTarget && (
        <AdminConfirmDialog title={t("groups.delete")} confirmLabel={t("groups.delete")} cancelLabel={tCommon("actions.cancel")}
          onConfirm={remove} onClose={() => setDeleteTarget(null)}>
          {t("groups.delete_confirm", { name: deleteTarget.name })}
        </AdminConfirmDialog>
      )}
    </AdminPanel>
  )
}
