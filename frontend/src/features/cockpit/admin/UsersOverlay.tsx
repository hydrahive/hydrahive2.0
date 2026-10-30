import { useCallback, useEffect, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { HelpButton } from "@/i18n/HelpButton"
import { ApiKeysSection } from "@/features/users/ApiKeysSection"
import { GroupsSection } from "@/features/access/GroupsSection"
import { ChangePasswordDialog } from "@/features/users/ChangePasswordDialog"
import { EditUserDialog } from "@/features/users/EditUserDialog"
import { NewUserDialog } from "@/features/users/NewUserDialog"
import { usersApi } from "@/features/users/api"
import { DeleteDialog } from "@/features/archive/delete/DeleteDialog"
import type { User } from "@/features/users/types"
import { CockpitButton } from "../CockpitButton"
import { AdminFeedback, AdminTabs } from "./ui"
import { UserRows } from "./UserRows"
import { parseUsersTab, USERS_TABS, type UsersTab } from "./usersTabs"
import { AdminOverlay } from "./AdminOverlay"
import { ADMIN_OVERLAY_THEME } from "@/shared/brand/boxThemes"

export function UsersOverlay({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("users")
  const { t: tCommon } = useTranslation("common")
  const currentUsername = useAuthStore((state) => state.username) ?? ""
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [actionError, setActionError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [showNew, setShowNew] = useState(false)
  const [passwordTarget, setPasswordTarget] = useState<string | null>(null)
  const [editTarget, setEditTarget] = useState<User | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = parseUsersTab(searchParams.get("tab"))
  function selectTab(next: UsersTab) {
    const params = new URLSearchParams(searchParams)
    params.set("tab", next)
    setSearchParams(params, { replace: true })
  }

  const load = useCallback(async () => {
    try {
      setUsers(await usersApi.list())
      setActionError(null)
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : tCommon("status.error"))
    } finally {
      setLoading(false)
    }
  }, [tCommon])

  useEffect(() => {
    const initial = window.setTimeout(load, 0)
    return () => window.clearTimeout(initial)
  }, [load])

  return (
    <AdminOverlay theme={ADMIN_OVERLAY_THEME["users"]}
      eyebrow="Admin"
      title={t("title")}
      onClose={onClose}
      headerActions={(
        <div className="flex items-center gap-2">
          <HelpButton topic="users" />
          {/* Gruppen und API-Keys haben eigene Anlege-Knöpfe – „Neuer Benutzer“ nur im Reiter Benutzer. */}
          {tab === "benutzer" && (
            <CockpitButton tone="primary" onClick={() => setShowNew(true)}>
              <Plus size={13} className="mr-1 inline" />{t("actions.new")}
            </CockpitButton>
          )}
        </div>
      )}
    >
      <div className="space-y-5">
        <p className="text-sm text-[#9aa7bc]">{t("subtitle")}</p>
        {actionError && <AdminFeedback tone="danger">{actionError}</AdminFeedback>}
        {notice && <AdminFeedback tone="success">{notice}</AdminFeedback>}
        <AdminTabs label={t("title")} idPrefix="users" active={tab} onSelect={selectTab}
          tabs={USERS_TABS.map((id) => ({ id, label: t(`tabs.${id}`), ...(id === "benutzer" ? { count: users.length } : {}) }))}>
          {tab === "benutzer" && (
            loading ? <AdminFeedback loading>Benutzer werden geladen …</AdminFeedback>
              : !actionError && users.length === 0 ? <AdminFeedback>{t("no_users")}</AdminFeedback>
                : <UserRows users={users} currentUsername={currentUsername} onEdit={setEditTarget} onPassword={setPasswordTarget}
                    onDelete={setDeleteTarget} onNotice={(m) => { setActionError(null); setNotice(m) }}
                    onError={(m) => { setNotice(null); setActionError(m) }} />
          )}
          {tab === "gruppen" && <GroupsSection users={users} />}
          {tab === "api-keys" && <ApiKeysSection />}
        </AdminTabs>
      </div>

      {showNew && <NewUserDialog onClose={() => setShowNew(false)} onCreated={() => { setShowNew(false); load() }} />}
      {passwordTarget && <ChangePasswordDialog username={passwordTarget} onClose={() => setPasswordTarget(null)} onChanged={() => setPasswordTarget(null)} />}
      {editTarget && <EditUserDialog user={editTarget} onClose={() => setEditTarget(null)} onSaved={() => { setEditTarget(null); load() }} />}
      {deleteTarget && deleteTarget !== currentUsername && (
        <DeleteDialog kind="user" id={deleteTarget} onClose={() => setDeleteTarget(null)} onDeleted={() => { void load() }} />
      )}
    </AdminOverlay>
  )
}
