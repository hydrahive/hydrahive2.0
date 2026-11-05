import { useEffect, type Dispatch, type MutableRefObject, type SetStateAction } from "react"
import { chatApi } from "./api"
import { mergeSessionPages, sessionMatchesScope } from "./_sessionPages"
import type { Session } from "./types"

type Scope = string | null | undefined

interface Options {
  deepLinkSid: string | null
  openSessionRequest: string | null
  projectId: Scope
  sessions: Session[]
  appliedDeepLinkRef: MutableRefObject<string | null>
  sessionScopeRef: MutableRefObject<Scope>
  deletedSessionIdsRef: MutableRefObject<Set<string>>
  setSessions: Dispatch<SetStateAction<Session[]>>
  setActiveId: Dispatch<SetStateAction<string | null>>
  setLoadError: Dispatch<SetStateAction<string | null>>
  onSessionRequestHandled?: () => void
  t: (key: string) => string
}

/** Öffnet einzelne Sessions aus URL oder fremdem Cockpit-Panel, unabhängig von der geladenen Seite. */
export function useRequestedSessions({
  deepLinkSid, openSessionRequest, projectId, sessions, appliedDeepLinkRef, sessionScopeRef,
  deletedSessionIdsRef, setSessions, setActiveId, setLoadError, onSessionRequestHandled, t,
}: Options) {
  useEffect(() => {
    if (!deepLinkSid) {
      appliedDeepLinkRef.current = null
      return
    }
    if (appliedDeepLinkRef.current === deepLinkSid || deletedSessionIdsRef.current.has(deepLinkSid)) return
    const requestedScope = projectId
    let cancelled = false
    void chatApi.getSession(deepLinkSid)
      .then((linked) => {
        if (cancelled || !Object.is(sessionScopeRef.current, requestedScope)) return
        if (!sessionMatchesScope(linked, requestedScope)) return setLoadError(t("session.request_wrong_scope"))
        setSessions((current) => mergeSessionPages(current, [linked]))
        appliedDeepLinkRef.current = deepLinkSid
        setActiveId(deepLinkSid)
      })
      .catch(() => {
        if (!cancelled && Object.is(sessionScopeRef.current, requestedScope)) {
          setLoadError(t("session.request_failed"))
        }
      })
    return () => { cancelled = true }
  }, [appliedDeepLinkRef, deepLinkSid, deletedSessionIdsRef, projectId, sessionScopeRef, setActiveId, setLoadError, setSessions, t])

  useEffect(() => {
    if (!openSessionRequest) return
    if (deletedSessionIdsRef.current.has(openSessionRequest)) {
      onSessionRequestHandled?.()
      return
    }
    const requestedScope = projectId
    const known = sessions.find((session) => session.id === openSessionRequest)
    if (known) {
      if (sessionMatchesScope(known, requestedScope)) setActiveId(openSessionRequest)
      else setLoadError(t("session.request_wrong_scope"))
      onSessionRequestHandled?.()
      return
    }
    let cancelled = false
    void chatApi.getSession(openSessionRequest)
      .then((requested) => {
        if (cancelled || !Object.is(sessionScopeRef.current, requestedScope)) return
        if (!sessionMatchesScope(requested, requestedScope)) {
          setLoadError(t("session.request_wrong_scope"))
          onSessionRequestHandled?.()
          return
        }
        setSessions((current) => mergeSessionPages(current, [requested]))
        setActiveId(requested.id)
        onSessionRequestHandled?.()
      })
      .catch(() => {
        if (cancelled || !Object.is(sessionScopeRef.current, requestedScope)) return
        setLoadError(t("session.request_failed"))
        onSessionRequestHandled?.()
      })
    return () => { cancelled = true }
    // sessions absichtlich nicht: Unbekanntes direkt laden statt Seite 1 zu pollen.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deletedSessionIdsRef, onSessionRequestHandled, openSessionRequest, projectId, sessionScopeRef, setActiveId, setLoadError, setSessions, t])
}
