import { useEffect, useMemo, useRef, useState } from "react"
import { buddyApi, type BuddyCockpitPrefs, type BuddyCockpitSlotId, type BuddyDecorVariant } from "./api"

export const DEFAULT_BUDDY_COCKPIT_PREFS: BuddyCockpitPrefs = {
  version: 1,
  slots: {
    music: { visible: true, collapsed: true },
    extensions: { visible: true, collapsed: true },
    moduleWidgets: { visible: true, collapsed: false },
    futureBottom: { visible: false, collapsed: true },
  },
  rightRailCollapsed: false,
  decorVariant: "default",
}

const SLOT_IDS: BuddyCockpitSlotId[] = ["music", "extensions", "moduleWidgets", "futureBottom"]
const DECOR_VARIANTS: BuddyDecorVariant[] = ["default", "calm", "aurora", "minimal"]

export function normalizeCockpitPrefs(raw: Partial<BuddyCockpitPrefs> | null | undefined): BuddyCockpitPrefs {
  const slots = { ...DEFAULT_BUDDY_COCKPIT_PREFS.slots }
  for (const id of SLOT_IDS) {
    const incoming = raw?.slots?.[id]
    slots[id] = {
      visible: typeof incoming?.visible === "boolean" ? incoming.visible : DEFAULT_BUDDY_COCKPIT_PREFS.slots[id].visible,
      collapsed: typeof incoming?.collapsed === "boolean" ? incoming.collapsed : DEFAULT_BUDDY_COCKPIT_PREFS.slots[id].collapsed,
    }
  }
  const decorVariant = raw?.decorVariant && DECOR_VARIANTS.includes(raw.decorVariant)
    ? raw.decorVariant
    : DEFAULT_BUDDY_COCKPIT_PREFS.decorVariant
  return {
    version: 1,
    slots,
    rightRailCollapsed: typeof raw?.rightRailCollapsed === "boolean"
      ? raw.rightRailCollapsed
      : DEFAULT_BUDDY_COCKPIT_PREFS.rightRailCollapsed,
    decorVariant,
  }
}

export function useBuddyCockpitPrefs() {
  const [prefs, setPrefs] = useState<BuddyCockpitPrefs>(DEFAULT_BUDDY_COCKPIT_PREFS)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const loadedRef = useRef(false)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let active = true
    buddyApi.getCockpitPrefs()
      .then((serverPrefs) => {
        if (!active) return
        setPrefs(normalizeCockpitPrefs(serverPrefs))
        setError(null)
      })
      .catch((e: unknown) => {
        if (!active) return
        setError(e instanceof Error ? e.message : "cockpit-prefs")
      })
      .finally(() => {
        if (!active) return
        loadedRef.current = true
        setLoading(false)
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!loadedRef.current) return
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      buddyApi.putCockpitPrefs(prefs)
        .then((result) => {
          setPrefs(normalizeCockpitPrefs(result.cockpit_prefs))
          setError(null)
        })
        .catch((e: unknown) => {
          console.warn("Could not save Buddy cockpit prefs", e)
          setError(e instanceof Error ? e.message : "cockpit-prefs-save")
        })
    }, 500)
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current)
    }
  }, [prefs])

  const actions = useMemo(() => ({
    setSlotVisible: (slot: BuddyCockpitSlotId, visible: boolean) => {
      setPrefs((current) => normalizeCockpitPrefs({
        ...current,
        slots: { ...current.slots, [slot]: { ...current.slots[slot], visible } },
      }))
    },
    setSlotCollapsed: (slot: BuddyCockpitSlotId, collapsed: boolean) => {
      setPrefs((current) => normalizeCockpitPrefs({
        ...current,
        slots: { ...current.slots, [slot]: { ...current.slots[slot], collapsed } },
      }))
    },
    setRightRailCollapsed: (collapsed: boolean) => {
      setPrefs((current) => normalizeCockpitPrefs({ ...current, rightRailCollapsed: collapsed }))
    },
    setDecorVariant: (decorVariant: BuddyDecorVariant) => {
      setPrefs((current) => normalizeCockpitPrefs({ ...current, decorVariant }))
    },
  }), [])

  return { prefs, setPrefs, loading, error, ...actions }
}
