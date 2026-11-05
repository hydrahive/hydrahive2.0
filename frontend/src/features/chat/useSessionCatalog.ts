import { useEffect, useMemo, useRef, useState } from "react"
import { chatApi, type ProjectBrief } from "./api"
import { mergeSessionPages, sessionMatchesScope } from "./_sessionPages"
import { pickSessionFor } from "./_pickSession"
import { forgetDeleted, readStoredSession, rememberActive } from "./_storedSession"
import type { AgentBrief, Session } from "./types"
import { useRequestedSessions } from "./useRequestedSessions"

const SESSION_PAGE_SIZE = 50

type Scope = string | null | undefined

interface UseSessionCatalogOptions {
  deepLinkSid: string | null
  projectId: Scope
  preferredAgentId: string | null
  agentSelectionExplicit: boolean
  openSessionRequest: string | null
  onSessionRequestHandled?: () => void
  onSessionCreated?: () => void
  t: (key: string) => string
}

/** Verwaltet den paginierten Sitzungskatalog einschließlich externer Öffnungsanfragen. */
export function useSessionCatalog({
  deepLinkSid, projectId, preferredAgentId, agentSelectionExplicit,
  openSessionRequest, onSessionRequestHandled, onSessionCreated, t,
}: UseSessionCatalogOptions) {
  const appliedDeepLink = useRef<string | null>(null)
  const sessionScopeGeneration = useRef(0)
  const sessionCatalogRevision = useRef(0)
  const sessionScope = useRef<Scope>(projectId)
  const deletedSessionIds = useRef(new Set<string>())
  const [sessions, setSessions] = useState<Session[]>([])
  const [agents, setAgents] = useState<AgentBrief[]>([])
  const [projects, setProjects] = useState<ProjectBrief[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [sessionTotal, setSessionTotal] = useState(0)
  const [hasMoreSessions, setHasMoreSessions] = useState(false)
  const [nextSessionOffset, setNextSessionOffset] = useState(0)
  const [loadingMoreSessions, setLoadingMoreSessions] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [newSessionBusy, setNewSessionBusy] = useState(false)

  async function loadAll(reset = false, generation = sessionScopeGeneration.current, revision = sessionCatalogRevision.current) {
    const requestedScope = projectId
    try {
      const [page, loadedAgents, loadedProjects] = await Promise.all([
        chatApi.listSessionPage({ limit: SESSION_PAGE_SIZE, offset: 0, projectId: requestedScope }),
        chatApi.listAgents(),
        chatApi.listProjects(),
      ])
      if (!isCurrent(generation, revision, requestedScope)) return
      const loadedSessions = page.items.filter((session) => !deletedSessionIds.current.has(session.id))
      setSessions((current) => {
        if (!reset) return mergeSessionPages(current, loadedSessions)
        const requestedIds = new Set([deepLinkSid, openSessionRequest].filter(Boolean))
        const requested = current.filter((session) =>
          requestedIds.has(session.id) && !deletedSessionIds.current.has(session.id) && sessionMatchesScope(session, requestedScope))
        return mergeSessionPages(loadedSessions, requested)
      })
      setSessionTotal(page.total)
      setHasMoreSessions(reset ? page.has_more : sessions.length < page.total)
      if (reset) setNextSessionOffset(page.offset + page.items.length)
      setAgents(loadedAgents)
      setProjects(loadedProjects)
      setLoadError(null)
      if (!activeId && !deepLinkSid && loadedSessions.length > 0) {
        setActiveId(pickSessionFor(loadedSessions, preferredAgentId, readStoredSession(requestedScope ?? null), { agentExplicit: agentSelectionExplicit }))
      }
    } catch {
      if (isCurrent(generation, revision, requestedScope)) setLoadError(t("session.list_failed"))
    }
  }

  function isCurrent(generation: number, revision: number, requestedScope: Scope) {
    return generation === sessionScopeGeneration.current
      && revision === sessionCatalogRevision.current
      && Object.is(sessionScope.current, requestedScope)
  }

  async function loadMoreSessions() {
    if (loadingMoreSessions || !hasMoreSessions) return
    const generation = sessionScopeGeneration.current
    const revision = sessionCatalogRevision.current
    const requestedScope = projectId
    setLoadingMoreSessions(true)
    try {
      const page = await chatApi.listSessionPage({ limit: SESSION_PAGE_SIZE, offset: nextSessionOffset, projectId: requestedScope })
      if (!isCurrent(generation, revision, requestedScope)) return
      const incoming = page.items.filter((session) => !deletedSessionIds.current.has(session.id))
      setSessions((current) => mergeSessionPages(current, incoming))
      setSessionTotal(page.total)
      setHasMoreSessions(page.has_more)
      setNextSessionOffset(page.offset + page.items.length)
      setLoadError(null)
    } catch {
      if (isCurrent(generation, revision, requestedScope)) setLoadError(t("session.list_failed"))
    } finally {
      if (isCurrent(generation, revision, requestedScope)) setLoadingMoreSessions(false)
    }
  }

  useEffect(() => {
    sessionScope.current = projectId
    const generation = ++sessionScopeGeneration.current
    const revision = ++sessionCatalogRevision.current
    // Scope-Wechsel muss den alten Katalog synchron ausblenden, bevor die neue Antwort eintrifft.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSessions([])
    setSessionTotal(0)
    setHasMoreSessions(false)
    setNextSessionOffset(0)
    setLoadingMoreSessions(false)
    void loadAll(true, generation, revision)
    // loadAll benutzt stets die Werte dieses Renders.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  useRequestedSessions({
    deepLinkSid, openSessionRequest, projectId, sessions,
    appliedDeepLinkRef: appliedDeepLink, sessionScopeRef: sessionScope,
    deletedSessionIdsRef: deletedSessionIds,
    setSessions, setActiveId, setLoadError, onSessionRequestHandled, t,
  })

  const visibleSessions = useMemo(
    () => projectId === undefined ? sessions : sessions.filter((session) => session.project_id === projectId),
    [sessions, projectId],
  )
  const activeSession = visibleSessions.find((session) => session.id === activeId) ?? null
  const activeAgent = activeSession ? (agents.find((agent) => agent.id === activeSession.agent_id) ?? null) : null

  useEffect(() => {
    if (projectId === undefined || !activeId) return
    const current = sessions.find((session) => session.id === activeId)
    // Aktive Auswahl gehört zum Scope und darf beim Wechsel nicht stehen bleiben.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (current && current.project_id !== projectId) setActiveId(null)
  }, [projectId, activeId, sessions])

  useEffect(() => {
    if (activeId || deepLinkSid || visibleSessions.length === 0) return
    // Initiale Sessionwahl folgt unmittelbar aus der neu geladenen sichtbaren Liste.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setActiveId(pickSessionFor(visibleSessions, preferredAgentId, readStoredSession(projectId ?? null), { agentExplicit: agentSelectionExplicit }))
  }, [activeId, deepLinkSid, visibleSessions, preferredAgentId, projectId, agentSelectionExplicit])

  useEffect(() => {
    if (activeId) rememberActive(projectId, sessions.find((session) => session.id === activeId))
  }, [projectId, activeId, sessions])

  async function handleNew(agentId: string, title: string, newProjectId?: string) {
    const generation = sessionScopeGeneration.current
    const startingRevision = sessionCatalogRevision.current
    const requestedScope = projectId
    if (activeSession?.project_id) await chatApi.handover(activeSession.id)
    if (!isCurrent(generation, startingRevision, requestedScope)) return
    const created = await chatApi.createSession(agentId, title || undefined, newProjectId)
    onSessionCreated?.()
    if (!isCurrent(generation, startingRevision, requestedScope)) return
    const revision = ++sessionCatalogRevision.current
    await loadAll(true, generation, revision)
    if (isCurrent(generation, revision, requestedScope) && sessionMatchesScope(created, requestedScope)) setActiveId(created.id)
  }

  async function handleDelete(id: string) {
    const generation = sessionScopeGeneration.current
    const requestedScope = projectId
    await chatApi.deleteSession(id)
    const revision = ++sessionCatalogRevision.current
    deletedSessionIds.current.add(id)
    setSessions((current) => current.filter((session) => session.id !== id))
    if (activeId === id) {
      setActiveId(null)
      forgetDeleted(requestedScope, id)
    }
    if (generation === sessionScopeGeneration.current && Object.is(sessionScope.current, requestedScope)) {
      await loadAll(true, generation, revision)
    }
  }

  async function createPreferredSession() {
    const preferredAgent = preferredAgentId ? (agents.find((agent) => agent.id === preferredAgentId) ?? null) : null
    const agent = preferredAgent ?? activeAgent ?? agents.find((item) => !item.is_buddy) ?? agents[0]
    if (!agent) return
    const generation = sessionScopeGeneration.current
    const startingRevision = sessionCatalogRevision.current
    const requestedScope = projectId
    setNewSessionBusy(true)
    try {
      if (activeSession?.project_id) await chatApi.handover(activeSession.id)
      if (!isCurrent(generation, startingRevision, requestedScope)) return
      const created = await chatApi.createSession(agent.id, undefined, requestedScope ?? undefined)
      if (!isCurrent(generation, startingRevision, requestedScope)) return
      const revision = ++sessionCatalogRevision.current
      await loadAll(true, generation, revision)
      if (isCurrent(generation, revision, requestedScope)) setActiveId(created.id)
    } finally {
      setNewSessionBusy(false)
    }
  }

  const handleSessionChanged = (updated: Session) =>
    setSessions((current) => current.map((session) => session.id === updated.id ? updated : session))

  return {
    sessions, agents, setAgents, projects, activeId, setActiveId, activeSession, activeAgent,
    visibleSessions, sessionTotal, hasMoreSessions, loadingMoreSessions, loadMoreSessions,
    loadError, refreshCatalog: loadAll, handleNew, handleDelete, createPreferredSession,
    newSessionBusy, handleSessionChanged,
  }
}
