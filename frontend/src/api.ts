import type {
  AuditEntry,
  Client,
  Dashboard,
  DocumentRecord,
  Requirement,
} from "./types"

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api"

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const payload = (await response.json()) as { detail?: string }
      message = payload.detail || message
    } catch {
      // The fallback status message is sufficient for non-JSON errors.
    }
    throw new Error(message)
  }
  return (await response.json()) as T
}

export const api = {
  dashboard: () => request<Dashboard>("/dashboard"),
  clients: () => request<Client[]>("/clients"),
  requirements: () => request<Requirement[]>("/requirements"),
  documents: () => request<DocumentRecord[]>("/documents"),
  audit: () => request<AuditEntry[]>("/audit"),
  documentTypes: () => request<Record<string, string>>("/meta/document-types"),
  createClient: (payload: { name: string; email: string; industry: string }) =>
    request<Client>("/clients", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  createRequirement: (payload: {
    client_id: number
    period: string
    document_type: string
    due_date: string
  }) =>
    request<Requirement>("/requirements", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  uploadDocument: (payload: { clientId: number; requirementId?: number; file: File }) => {
    const body = new FormData()
    body.append("client_id", String(payload.clientId))
    if (payload.requirementId) body.append("requirement_id", String(payload.requirementId))
    body.append("file", payload.file)
    return request<DocumentRecord>("/documents/upload", { method: "POST", body })
  },
  reviewDocument: (id: number, decision: "approve" | "reject", notes = "") =>
    request<DocumentRecord>(`/documents/${id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision, notes }),
    }),
  sendReminder: (id: number) =>
    request<{ id: number; status: string }>(`/requirements/${id}/remind`, {
      method: "POST",
    }),
  exportUrl: `${API_BASE}/export/requirements.csv`,
}
