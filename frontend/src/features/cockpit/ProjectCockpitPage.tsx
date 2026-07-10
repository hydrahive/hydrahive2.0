import { CockpitPlaceholderPage } from "./CockpitPlaceholderPage"

export function ProjectCockpitPage() {
  return (
    <CockpitPlaceholderPage
      kind="projects"
      eyebrow="Projekte"
      title="Projekt-Cockpit"
      description="Ein Projekt öffnen und dort Chat, Agenten, Sessions, Dateien, Git/Gitea, Tasks und Datamining bündeln."
      mockupPath="/mockups/cockpit-v2/index.html"
      bullets={[
        "Projekt-Dropdown serverseitig persistent",
        "vollwertiger Projekt-Chat in der Mitte",
        "Agenten, Modell/Tiefe und Git links",
        "Dateien, Git Tree und Projekt-Tasks rechts",
      ]}
    />
  )
}
