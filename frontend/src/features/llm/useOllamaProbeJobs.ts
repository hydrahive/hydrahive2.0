import { useCallback, useEffect, useState } from "react"
import { ollamaCatalogApi, type OllamaProbeJob } from "./ollamaApi"

export function useOllamaProbeJobs() {
  const [probeJobs, setProbeJobs] = useState<Record<string, OllamaProbeJob>>({})

  const startProbe = useCallback(async (model: string) => {
    const job = await ollamaCatalogApi.probe(model)
    setProbeJobs((current) => ({ ...current, [model]: job }))
  }, [])

  useEffect(() => {
    const active = Object.values(probeJobs).filter((job) => job.status === "queued" || job.status === "running")
    if (!active.length) return
    const timer = window.setInterval(() => {
      void Promise.all(active.map((job) => ollamaCatalogApi.probeStatus(job.id))).then((updates) => {
        setProbeJobs((current) => {
          const next = { ...current }
          updates.forEach((job) => { next[job.model] = job })
          return next
        })
      }).catch(() => undefined)
    }, 1500)
    return () => window.clearInterval(timer)
  }, [probeJobs])

  return { probeJobs, startProbe }
}
