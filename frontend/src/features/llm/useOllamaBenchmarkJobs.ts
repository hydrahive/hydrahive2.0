import { useCallback, useEffect, useState } from "react"
import { ollamaCatalogApi, type OllamaBenchmarkJob } from "./ollamaApi"

export function useOllamaBenchmarkJobs() {
  const [benchmarkJobs, setBenchmarkJobs] = useState<Record<string, OllamaBenchmarkJob>>({})
  const startBenchmark = useCallback(async (model: string) => {
    const job = await ollamaCatalogApi.benchmark(model)
    setBenchmarkJobs((current) => ({ ...current, [model]: job }))
  }, [])
  useEffect(() => {
    const active = Object.values(benchmarkJobs).filter((job) => job.status === "queued" || job.status === "running")
    if (!active.length) return
    const timer = window.setInterval(() => {
      void Promise.all(active.map((job) => ollamaCatalogApi.benchmarkStatus(job.id))).then((updates) => {
        setBenchmarkJobs((current) => {
          const next = { ...current }
          updates.forEach((job) => { next[job.model] = job })
          return next
        })
      }).catch(() => undefined)
    }, 1500)
    return () => window.clearInterval(timer)
  }, [benchmarkJobs])
  return { benchmarkJobs, startBenchmark }
}
