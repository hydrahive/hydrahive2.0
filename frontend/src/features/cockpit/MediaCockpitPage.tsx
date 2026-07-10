import { CockpitPlaceholderPage } from "./CockpitPlaceholderPage"

export function MediaCockpitPage() {
  return (
    <CockpitPlaceholderPage
      kind="media"
      eyebrow="Media"
      title="Media-Cockpit"
      description="Die Produktionsstrecke vom ersten Prompt über Regie, Assets, Clips und Musik bis zum Schnitt."
      mockupPath="/mockups/media-cockpit-v1/index.html"
      bullets={[
        "Atelier als Hauptmotor",
        "Regie, Storyboard und Charaktere bündeln",
        "Bild, Video, Musik und Voice verknüpfen",
        "Videoeditor/Timeline einbetten statt neu bauen",
      ]}
    />
  )
}
