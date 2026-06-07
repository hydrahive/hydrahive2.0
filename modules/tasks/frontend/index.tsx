import { TaskBuddyBox } from "./components/TaskBuddyBox"
import { TaskPanel } from "./components/TaskPanel"

export const routes = [] as const

export const buddyWidgets = [TaskBuddyBox]

export const workspaceTabs = [{ id: "tasks", label: "Tasks", component: TaskPanel }]

export const nav = [] as const

export const i18n = {
  de: { tasks: { title: "Aufgaben" } },
  en: { tasks: { title: "Tasks" } },
}
