import { useState, useCallback } from "react"
import { workspaceApi, type FileContent } from "./api"

export function useWorkspace(agentId: string | null) {
  const [openFile, setOpenFile] = useState<FileContent | null>(null)
  const [error, setError] = useState<string | null>(null)

  const open = useCallback(async (path: string) => {
    if (!agentId) return
    setError(null)
    try {
      setOpenFile(await workspaceApi.file(agentId, path))
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [agentId])

  const save = useCallback(async (content: string) => {
    if (!agentId || !openFile) return
    await workspaceApi.save(agentId, openFile.path, content)
    setOpenFile({ ...openFile, content })
  }, [agentId, openFile])

  return { openFile, setOpenFile, open, save, error }
}
