export type CredentialType = "bearer" | "basic" | "cookie" | "header" | "query"

export interface Credential {
  name: string
  type: CredentialType
  value: string  // beim Listing leer (gemaskt)
  value_set: boolean
  url_pattern: string
  description: string
  header_name: string
  query_param: string
}

export interface CredentialSavePayload {
  name: string
  type: CredentialType
  value: string
  url_pattern: string
  description: string
  header_name: string
  query_param: string
}
