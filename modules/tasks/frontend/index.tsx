import { TaskBuddyBox } from "./components/TaskBuddyBox"

export { TaskPanel } from "./components/TaskPanel"

export const routes = [] as const

export const buddyWidgets = [TaskBuddyBox]

export const nav = [] as const

export const i18n = {
  de: { tasks: { title: "Aufgaben" } },
  en: { tasks: { title: "Tasks" } },
}
