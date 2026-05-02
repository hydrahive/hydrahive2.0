import { Crown, User as UserIcon } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { LanguageSwitcher } from "@/i18n/LanguageSwitcher"
import { ChangeOwnPasswordCard } from "./ChangeOwnPasswordCard"
import { ThemeSwitcher } from "./ThemeSwitcher"
import { TTSSettings } from "./TTSSettings"
import { LandingSwitcher } from "./LandingSwitcher"

export function ProfilePage() {
  const { t } = useTranslation("profile")
  const { t: tUsers } = useTranslation("users")
  const username = useAuthStore((s) => s.username) ?? ""
  const role = useAuthStore((s) => s.role) ?? "user"
  const RoleIcon = role === "admin" ? Crown : UserIcon

  return (
    <div className="space-y-5 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-white">{t("title")}</h1>
        <p className="text-zinc-500 text-sm mt-0.5">{t("subtitle")}</p>
      </div>

      <div className="flex items-center gap-4 p-5 rounded-xl border border-white/[8%] bg-white/[3%]">
        <div className="w-14 h-14 rounded-full bg-gradient-to-br from-indigo-500 to-violet-700 flex items-center justify-center text-white text-xl font-bold shadow-md shadow-violet-900/30 flex-shrink-0">
          {username[0]?.toUpperCase() ?? "?"}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-base font-medium text-zinc-100 truncate">{username}</p>
          <p className="text-xs text-zinc-500 mt-0.5 flex items-center gap-1.5">
            <RoleIcon size={12} className={role === "admin" ? "text-violet-400" : "text-zinc-500"} />
            {tUsers(`role.${role}`)}
          </p>
        </div>
      </div>

      <ChangeOwnPasswordCard />

      <div className="rounded-xl border border-white/[8%] bg-white/[2%] p-5 space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-zinc-200">{t("language.title")}</h2>
          <p className="text-xs text-zinc-500 mt-0.5">{t("language.description")}</p>
        </div>
        <div className="max-w-[200px]">
          <LanguageSwitcher />
        </div>
      </div>

      <ThemeSwitcher />

      <LandingSwitcher />

      <TTSSettings />
    </div>
  )
}
