export type Status =
  | "received"
  | "missing"
  | "late"
  | "in_review"
  | "approved"
  | "rejected"
  | "ready"
  | "needs_review"

export interface AuditEntry {
  id: number
  action: string
  entity_type: string
  entity_id: number | null
  actor: string
  detail: string
  created_at: string
}

export interface Client {
  id: number
  name: string
  email: string
  industry: string
  status: string
  created_at: string
  requirement_count: number
  completion_rate: number
}

export interface Requirement {
  id: number
  client_id: number
  client_name: string
  client_email: string
  period: string
  document_type: string
  due_date: string
  status: Status
  reminder_count: number
  latest_document_id: number | null
}

export interface ExtractedData {
  document_type?: string
  period?: string | null
  fields?: Record<string, string>
  warnings?: string[]
  text_characters?: number
  extraction_method?: string
  matched_requirement_id?: number
}

export interface DocumentRecord {
  id: number
  client_id: number
  client_name: string
  requirement_id: number | null
  original_filename: string
  content_type: string
  size_bytes: number
  document_type: string
  period: string | null
  status: Status
  confidence: number
  extracted_data: ExtractedData
  review_notes: string
  created_at: string
  reviewed_at: string | null
}

export interface Dashboard {
  clients: number
  requirements: number
  completion_rate: number
  received: number
  missing: number
  late: number
  in_review: number
  review_queue: number
  reminders_sent: number
  period_label: string
  recent_documents: DocumentRecord[]
  recent_activity: AuditEntry[]
}
