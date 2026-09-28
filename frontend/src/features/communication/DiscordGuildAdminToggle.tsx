/**
 * Häkchen „Server verwalten“ pro Discord-Server im Kanalkatalog.
 * Gibt die Verwaltungswerkzeuge (Kanäle, Rollen, Mitglieder) für diesen Server
 * frei (docs/specs/discord-server-admin-tools.md). Ohne passende Bot-Rechte
 * ist das Häkchen deaktiviert.
 */
import { Crown } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { DiscordCatalogGuild } from "./api"

interface Props {
  guild: DiscordCatalogGuild
  checked: boolean
  onToggle: (guildId: string) => void
}

export function DiscordGuildAdminToggle({ guild, checked, onToggle }: Props) {
  const { t } = useTranslation("communication")
  const disabled = !guild.can_admin
  return (
    <label
      title={disabled ? t("discord.admin.no_rights") : t("discord.admin.hint")}
      className={`ml-auto flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-[10px] ${
        checked ? "bg-rose-400/15 text-rose-200" : disabled ? "text-zinc-700 cursor-not-allowed" : "text-zinc-500 hover:text-zinc-300 cursor-pointer"
      }`}
    >
      <input type="checkbox" checked={checked} disabled={disabled} onChange={() => onToggle(guild.id)}
        className="accent-rose-400 w-3 h-3" />
      <Crown size={11} />
      {t("discord.admin.label")}
    </label>
  )
}
