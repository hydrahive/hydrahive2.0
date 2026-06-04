import { ExamplePage } from "./ExamplePage"

export const routes = [
  { path: "/example", element: <ExamplePage /> },
]

export const nav = [
  {
    path: "/example",
    icon: "Boxes",
    labelKey: "example",
    group: "working",
    roles: [] as ("admin" | "user")[],
  },
]

export const i18n = {
  de: {
    example: {
      title: "Beispiel-Modul",
      add: "Hinzufügen",
      placeholder: "Notiz eingeben…",
      empty: "Noch keine Notizen.",
    },
  },
  en: {
    example: {
      title: "Example Module",
      add: "Add",
      placeholder: "Enter a note…",
      empty: "No notes yet.",
    },
  },
}
