import { useEffect, useState } from "react"
import { akteApi, type AkteSchemaResponse } from "./api"

let cache: AkteSchemaResponse | null = null
let pending: Promise<AkteSchemaResponse> | null = null

export function useAkteSchema(): AkteSchemaResponse | null {
  const [schema, setSchema] = useState<AkteSchemaResponse | null>(cache)

  useEffect(() => {
    if (cache) return
    if (!pending) {
      pending = akteApi.getSchema()
    }
    pending.then((s) => {
      cache = s
      setSchema(s)
    }).catch(() => {
      pending = null
    })
  }, [])

  return schema
}
