import { Crown, KeyRound, Trash2, User as UserIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { User } from "./types"

interface Props {
  users: User[]
  currentUsername: string
  onChangePassword: (username: string) => void
  onDelete: (username: string) => void
}

export function UserList({ users, currentUsername, onChangePassword, onDelete }: Props) {
  const { t } = useTranslation("users")

  if (users.length === 0) {
    return <p className="text-sm text-zinc-600 py-6 text-center">{t("no_users")}</p>
  }

  return (
    <div className="space-y-1.5">
      {users.map((u) => {
        const isSelf = u.username === currentUsername
        const Icon = u.role === "admin" ? Crown : UserIcon
        return (
          <div
            key={u.username}
            className="flex items-center gap-3 p-3 rounded-xl border border-white/[8%] bg-white/[3%]"
          >
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-violet-700 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
              {u.username[0]?.toUpperCase() ?? "?"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-zinc-200 truncate flex items-center gap-2">
                {u.username}
                {isSelf && <span className="text-[10px] text-zinc-500 font-normal">{t("you_marker")}</span>}
              </p>
              <p className="text-xs text-zinc-500 mt-0.5 flex items-center gap-1">
                <Icon size={11} className={u.role === "admin" ? "text-violet-400" : "text-zinc-500"} />
                {t(`role.${u.role}`)}
              </p>
            </div>
            <button
              onClick={() => onChangePassword(u.username)}
              title={t("actions.change_password")}
              className="p-2 rounded-lg text-zinc-500 hover:text-violet-300 hover:bg-violet-500/10 transition-colors"
            >
              <KeyRound size={14} />
            </button>
            <button
              onClick={() => onDelete(u.username)}
              disabled={isSelf}
              title={t("actions.delete")}
              className="p-2 rounded-lg text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <Trash2 size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}
