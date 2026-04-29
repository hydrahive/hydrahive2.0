import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { MessageCircle } from "lucide-react"
import { communicationApi } from "./api"
import { WhatsAppCard } from "./WhatsAppCard"

export function CommunicationPage() {
  const { t } = useTranslation("communication")
  const [channels, setChannels] = useState<{ name: string; label: string }[] | null>(null)

  useEffect(() => {
    communicationApi.channels().then(setChannels).catch(() => setChannels([]))
  }, [])

  const hasWhatsApp = channels?.some((c) => c.name === "whatsapp") ?? false

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <MessageCircle className="text-emerald-400" size={20} />
        <div>
          <h1 className="text-xl font-semibold text-zinc-100">{t("title")}</h1>
          <p className="text-xs text-zinc-500 mt-0.5">{t("subtitle")}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {hasWhatsApp ? (
          <WhatsAppCard />
        ) : channels === null ? null : (
          <div className="rounded-xl bg-white/[3%] border border-white/[6%] p-5">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center shrink-0">
                <MessageCircle className="text-white" size={20} />
              </div>
              <div>
                <h3 className="text-zinc-100 font-semibold">{t("whatsapp.label")}</h3>
                <p className="text-xs text-amber-300 mt-1">{t("whatsapp.bridge_unavailable")}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
