<script setup lang="ts">
import {
  Activity,
  Bell,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  Clock3,
  Download,
  FileCheck2,
  FileSearch,
  Files,
  Gauge,
  LayoutDashboard,
  Loader2,
  Menu,
  Plus,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Upload,
  UserPlus,
  Users,
  X,
  XCircle,
} from "@lucide/vue"
import { computed, onMounted, reactive, ref } from "vue"

import { api } from "./api"
import type {
  AuditEntry,
  Client,
  Dashboard,
  DocumentRecord,
  Requirement,
  Status,
} from "./types"

type View = "dashboard" | "requirements" | "documents" | "clients" | "activity"
type Modal = "upload" | "requirement" | "client" | "review" | null

const emptyDashboard: Dashboard = {
  clients: 0,
  requirements: 0,
  completion_rate: 0,
  received: 0,
  missing: 0,
  late: 0,
  in_review: 0,
  review_queue: 0,
  reminders_sent: 0,
  period_label: "",
  recent_documents: [],
  recent_activity: [],
}

const dashboard = ref<Dashboard>(emptyDashboard)
const clients = ref<Client[]>([])
const requirements = ref<Requirement[]>([])
const documents = ref<DocumentRecord[]>([])
const activity = ref<AuditEntry[]>([])
const documentTypes = ref<Record<string, string>>({})
const selectedView = ref<View>("dashboard")
const modal = ref<Modal>(null)
const selectedDocument = ref<DocumentRecord | null>(null)
const loading = ref(true)
const mutating = ref(false)
const mobileNavOpen = ref(false)
const query = ref("")
const statusFilter = ref("all")
const errorMessage = ref("")
const toast = ref("")

const today = new Date()
const nextWeek = new Date(today)
nextWeek.setDate(today.getDate() + 7)

const requirementForm = reactive({
  client_id: 0,
  period: today.toISOString().slice(0, 7),
  document_type: "invoice",
  due_date: nextWeek.toISOString().slice(0, 10),
})

const clientForm = reactive({ name: "", email: "", industry: "Professional services" })
const uploadForm = reactive<{ client_id: number; requirement_id?: number; file: File | null }>({
  client_id: 0,
  requirement_id: undefined,
  file: null,
})

const navItems: Array<{ id: View; label: string; icon: typeof LayoutDashboard }> = [
  { id: "dashboard", label: "Overview", icon: LayoutDashboard },
  { id: "requirements", label: "Collections", icon: FileCheck2 },
  { id: "documents", label: "Documents", icon: Files },
  { id: "clients", label: "Clients", icon: Users },
  { id: "activity", label: "Audit trail", icon: Activity },
]

const viewTitles: Record<View, { eyebrow: string; title: string; description: string }> = {
  dashboard: {
    eyebrow: "Operations overview",
    title: "Good morning, Alex",
    description: "Here is what needs your attention across this month's collection cycle.",
  },
  requirements: {
    eyebrow: "Collection control",
    title: "Document requirements",
    description: "Track every expected document, deadline, reminder, and completion state.",
  },
  documents: {
    eyebrow: "Human-in-the-loop review",
    title: "Document workspace",
    description: "Inspect extracted fields and approve only information you can verify.",
  },
  clients: {
    eyebrow: "Client portfolio",
    title: "Clients",
    description: "Monitor collection health and outstanding work by account.",
  },
  activity: {
    eyebrow: "Accountability",
    title: "Audit trail",
    description: "Review an immutable-style timeline of workflow decisions and actions.",
  },
}

const currentTitle = computed(() => viewTitles[selectedView.value])
const reviewDocuments = computed(() =>
  documents.value.filter((document) => ["needs_review", "ready"].includes(document.status)),
)
const filteredRequirements = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return requirements.value.filter((requirement) => {
    const statusMatches = statusFilter.value === "all" || requirement.status === statusFilter.value
    const queryMatches =
      !needle ||
      requirement.client_name.toLowerCase().includes(needle) ||
      documentLabel(requirement.document_type).toLowerCase().includes(needle) ||
      requirement.period.includes(needle)
    return statusMatches && queryMatches
  })
})
const filteredDocuments = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return documents.value.filter((document) => {
    const statusMatches = statusFilter.value === "all" || document.status === statusFilter.value
    const queryMatches =
      !needle ||
      document.client_name.toLowerCase().includes(needle) ||
      document.original_filename.toLowerCase().includes(needle) ||
      documentLabel(document.document_type).toLowerCase().includes(needle)
    return statusMatches && queryMatches
  })
})
const completionRing = computed(() => ({
  background: `conic-gradient(#dbff76 ${dashboard.value.completion_rate * 3.6}deg, #22324a 0deg)`,
}))

function notify(message: string): void {
  toast.value = message
  window.setTimeout(() => {
    if (toast.value === message) toast.value = ""
  }, 3200)
}

async function loadAll(showSpinner = true): Promise<void> {
  if (showSpinner) loading.value = true
  errorMessage.value = ""
  try {
    const [dashboardData, clientData, requirementData, documentData, auditData, typeData] =
      await Promise.all([
        api.dashboard(),
        api.clients(),
        api.requirements(),
        api.documents(),
        api.audit(),
        api.documentTypes(),
      ])
    dashboard.value = dashboardData
    clients.value = clientData
    requirements.value = requirementData
    documents.value = documentData
    activity.value = auditData
    documentTypes.value = typeData
    if (!requirementForm.client_id && clientData[0]) requirementForm.client_id = clientData[0].id
    if (!uploadForm.client_id && clientData[0]) uploadForm.client_id = clientData[0].id
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "Unable to load the workspace."
  } finally {
    loading.value = false
  }
}

function navigate(view: View): void {
  selectedView.value = view
  mobileNavOpen.value = false
  query.value = ""
  statusFilter.value = "all"
}

function openUpload(requirement?: Requirement): void {
  uploadForm.file = null
  uploadForm.requirement_id = requirement?.id
  uploadForm.client_id = requirement?.client_id || clients.value[0]?.id || 0
  modal.value = "upload"
}

function openReview(document: DocumentRecord): void {
  selectedDocument.value = document
  modal.value = "review"
}

async function submitUpload(): Promise<void> {
  if (!uploadForm.client_id || !uploadForm.file) return
  mutating.value = true
  try {
    const uploaded = await api.uploadDocument({
      clientId: uploadForm.client_id,
      requirementId: uploadForm.requirement_id,
      file: uploadForm.file,
    })
    modal.value = null
    await loadAll(false)
    notify(`${uploaded.original_filename} is ready for review.`)
  } catch (error) {
    notify(error instanceof Error ? error.message : "Upload failed.")
  } finally {
    mutating.value = false
  }
}

async function submitRequirement(): Promise<void> {
  if (!requirementForm.client_id) return
  mutating.value = true
  try {
    await api.createRequirement({ ...requirementForm })
    modal.value = null
    await loadAll(false)
    notify("Collection requirement created.")
  } catch (error) {
    notify(error instanceof Error ? error.message : "Could not create requirement.")
  } finally {
    mutating.value = false
  }
}

async function submitClient(): Promise<void> {
  if (!clientForm.name || !clientForm.email) return
  mutating.value = true
  try {
    await api.createClient({ ...clientForm })
    clientForm.name = ""
    clientForm.email = ""
    clientForm.industry = "Professional services"
    modal.value = null
    await loadAll(false)
    notify("Client added to the workspace.")
  } catch (error) {
    notify(error instanceof Error ? error.message : "Could not add client.")
  } finally {
    mutating.value = false
  }
}

async function review(decision: "approve" | "reject"): Promise<void> {
  if (!selectedDocument.value) return
  mutating.value = true
  try {
    await api.reviewDocument(
      selectedDocument.value.id,
      decision,
      decision === "approve" ? "Verified during human review." : "Rejected during human review.",
    )
    modal.value = null
    selectedDocument.value = null
    await loadAll(false)
    notify(decision === "approve" ? "Document approved and matched." : "Document rejected.")
  } catch (error) {
    notify(error instanceof Error ? error.message : "Review action failed.")
  } finally {
    mutating.value = false
  }
}

async function remind(requirement: Requirement): Promise<void> {
  mutating.value = true
  try {
    await api.sendReminder(requirement.id)
    await loadAll(false)
    notify(`Reminder sent to ${requirement.client_name}.`)
  } catch (error) {
    notify(error instanceof Error ? error.message : "Reminder failed.")
  } finally {
    mutating.value = false
  }
}

function documentLabel(value: string): string {
  return documentTypes.value[value] || value.replaceAll("_", " ")
}

function statusLabel(value: string): string {
  const labels: Record<string, string> = {
    received: "Received",
    missing: "Missing",
    late: "Overdue",
    in_review: "In review",
    approved: "Approved",
    rejected: "Rejected",
    ready: "Ready to review",
    needs_review: "Needs review",
  }
  return labels[value] || value.replaceAll("_", " ")
}

function statusClass(value: Status): string {
  return `status-${value.replaceAll("_", "-")}`
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(
    new Date(`${value}T00:00:00`),
  )
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value))
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

function actionIcon(action: string): typeof Upload {
  if (action.includes("approved")) return CheckCircle2
  if (action.includes("reminder")) return Send
  if (action.includes("client")) return UserPlus
  if (action.includes("requirement")) return CalendarDays
  return Upload
}

onMounted(() => loadAll())
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar" :class="{ 'sidebar-open': mobileNavOpen }">
      <div class="brand-row">
        <div class="brand-mark"><span></span><span></span><span></span></div>
        <div>
          <strong>LedgerFlow</strong>
          <small>Document operations</small>
        </div>
        <button class="icon-button mobile-close" aria-label="Close navigation" @click="mobileNavOpen = false">
          <X :size="18" />
        </button>
      </div>

      <div class="workspace-switcher">
        <div class="workspace-avatar">WF</div>
        <div><strong>Westfield & Co.</strong><span>Demo workspace</span></div>
        <ChevronRight :size="16" />
      </div>

      <nav class="main-nav" aria-label="Primary navigation">
        <p>Workspace</p>
        <button
          v-for="item in navItems"
          :key="item.id"
          :class="{ active: selectedView === item.id }"
          @click="navigate(item.id)"
        >
          <component :is="item.icon" :size="18" />
          <span>{{ item.label }}</span>
          <span v-if="item.id === 'documents' && dashboard.review_queue" class="nav-badge">
            {{ dashboard.review_queue }}
          </span>
        </button>
      </nav>

      <div class="sidebar-footer">
        <div class="security-card">
          <ShieldCheck :size="19" />
          <div><strong>Demo data only</strong><span>No client secrets stored</span></div>
        </div>
        <div class="profile-row">
          <div class="profile-avatar">AS</div>
          <div><strong>Alex Smith</strong><span>Workspace admin</span></div>
          <Bell :size="17" />
        </div>
      </div>
    </aside>

    <div v-if="mobileNavOpen" class="sidebar-scrim" @click="mobileNavOpen = false"></div>

    <main class="main-area">
      <header class="topbar">
        <button class="icon-button menu-button" aria-label="Open navigation" @click="mobileNavOpen = true">
          <Menu :size="20" />
        </button>
        <div class="global-search">
          <Search :size="18" />
          <input v-model="query" type="search" placeholder="Search clients, documents, periods..." />
          <kbd>⌘ K</kbd>
        </div>
        <div class="topbar-actions">
          <button class="button ghost hide-mobile" :disabled="loading" @click="loadAll()">
            <RefreshCw :size="16" :class="{ spinning: loading }" /> Refresh
          </button>
          <button class="button primary" @click="openUpload()"><Upload :size="16" /> Upload document</button>
        </div>
      </header>

      <div v-if="toast" class="toast"><CheckCircle2 :size="18" />{{ toast }}</div>

      <section class="content-wrap">
        <div class="page-heading">
          <div>
            <p class="eyebrow">{{ currentTitle.eyebrow }}</p>
            <h1>{{ currentTitle.title }}</h1>
            <p>{{ currentTitle.description }}</p>
          </div>
          <div v-if="selectedView !== 'dashboard'" class="heading-actions">
            <button v-if="selectedView === 'requirements'" class="button secondary" @click="modal = 'requirement'">
              <Plus :size="16" /> New requirement
            </button>
            <button v-if="selectedView === 'clients'" class="button secondary" @click="modal = 'client'">
              <UserPlus :size="16" /> Add client
            </button>
            <a v-if="selectedView === 'requirements'" class="button ghost" :href="api.exportUrl">
              <Download :size="16" /> Export CSV
            </a>
          </div>
        </div>

        <div v-if="errorMessage" class="error-banner">
          <CircleAlert :size="19" />
          <div><strong>Workspace unavailable</strong><span>{{ errorMessage }}</span></div>
          <button class="button ghost" @click="loadAll()">Try again</button>
        </div>

        <div v-if="loading" class="loading-panel">
          <Loader2 :size="28" class="spinning" />
          <strong>Loading document operations...</strong>
        </div>

        <template v-else-if="selectedView === 'dashboard'">
          <div class="metric-grid">
            <article class="metric-card metric-dark">
              <div class="metric-icon"><Gauge :size="20" /></div>
              <span>Collection health</span>
              <strong>{{ dashboard.completion_rate }}%</strong>
              <small><span class="positive-dot"></span>{{ dashboard.received }} of {{ dashboard.requirements }} complete</small>
            </article>
            <article class="metric-card">
              <div class="metric-icon mint"><FileCheck2 :size="20" /></div>
              <span>Documents received</span>
              <strong>{{ dashboard.received }}</strong>
              <small>{{ dashboard.period_label }}</small>
            </article>
            <article class="metric-card">
              <div class="metric-icon amber"><Clock3 :size="20" /></div>
              <span>Needs attention</span>
              <strong>{{ dashboard.late + dashboard.in_review }}</strong>
              <small>{{ dashboard.late }} overdue · {{ dashboard.in_review }} in review</small>
            </article>
            <article class="metric-card">
              <div class="metric-icon lilac"><Send :size="20" /></div>
              <span>Reminders logged</span>
              <strong>{{ dashboard.reminders_sent }}</strong>
              <small>Idempotent workflow actions</small>
            </article>
          </div>

          <div class="dashboard-grid">
            <article class="panel collection-panel">
              <div class="panel-heading">
                <div><p class="eyebrow">Live collection cycle</p><h2>{{ dashboard.period_label }}</h2></div>
                <button class="text-button" @click="navigate('requirements')">View all <ChevronRight :size="15" /></button>
              </div>
              <div class="collection-body">
                <div class="completion-ring" :style="completionRing">
                  <div><strong>{{ dashboard.completion_rate }}%</strong><span>complete</span></div>
                </div>
                <div class="status-breakdown">
                  <div><span class="status-dot received"></span><p><strong>Received</strong><small>Verified and complete</small></p><b>{{ dashboard.received }}</b></div>
                  <div><span class="status-dot review"></span><p><strong>In review</strong><small>Awaiting a human decision</small></p><b>{{ dashboard.in_review }}</b></div>
                  <div><span class="status-dot missing"></span><p><strong>Missing</strong><small>Before the due date</small></p><b>{{ dashboard.missing }}</b></div>
                  <div><span class="status-dot overdue"></span><p><strong>Overdue</strong><small>Escalation recommended</small></p><b>{{ dashboard.late }}</b></div>
                </div>
              </div>
            </article>

            <article class="panel automation-panel">
              <div class="sparkle"><Sparkles :size="20" /></div>
              <p class="eyebrow">Automation guard</p>
              <h2>Human judgment stays in control.</h2>
              <p>
                LedgerFlow extracts and routes documents, but low-confidence data is never accepted
                without review.
              </p>
              <div class="automation-stat">
                <div><FileSearch :size="18" /><span><strong>{{ dashboard.review_queue }}</strong> documents require review</span></div>
                <button class="button acid" @click="navigate('documents')">Open queue</button>
              </div>
            </article>
          </div>

          <div class="dashboard-grid lower-grid">
            <article class="panel table-panel">
              <div class="panel-heading">
                <div><p class="eyebrow">Latest arrivals</p><h2>Recent documents</h2></div>
                <button class="text-button" @click="navigate('documents')">Document workspace <ChevronRight :size="15" /></button>
              </div>
              <div class="table-wrap">
                <table>
                  <thead><tr><th>Document</th><th>Client</th><th>Confidence</th><th>Status</th><th></th></tr></thead>
                  <tbody>
                    <tr v-for="document in dashboard.recent_documents" :key="document.id">
                      <td><div class="file-cell"><span><Files :size="17" /></span><p><strong>{{ document.original_filename }}</strong><small>{{ documentLabel(document.document_type) }} · {{ formatBytes(document.size_bytes) }}</small></p></div></td>
                      <td>{{ document.client_name }}</td>
                      <td><div class="confidence"><span><i :style="{ width: `${document.confidence * 100}%` }"></i></span>{{ Math.round(document.confidence * 100) }}%</div></td>
                      <td><span class="status-pill" :class="statusClass(document.status)">{{ statusLabel(document.status) }}</span></td>
                      <td><button class="icon-button" aria-label="Review document" @click="openReview(document)"><ChevronRight :size="17" /></button></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </article>

            <article class="panel activity-panel">
              <div class="panel-heading"><div><p class="eyebrow">Traceable by design</p><h2>Recent activity</h2></div></div>
              <div class="timeline compact">
                <div v-for="entry in dashboard.recent_activity" :key="entry.id" class="timeline-item">
                  <span><component :is="actionIcon(entry.action)" :size="15" /></span>
                  <p><strong>{{ entry.detail }}</strong><small>{{ formatDateTime(entry.created_at) }}</small></p>
                </div>
              </div>
            </article>
          </div>
        </template>

        <template v-else-if="selectedView === 'requirements'">
          <div class="filterbar">
            <div class="filter-tabs">
              <button v-for="filter in ['all', 'missing', 'late', 'in_review', 'received']" :key="filter" :class="{ active: statusFilter === filter }" @click="statusFilter = filter">
                {{ filter === 'all' ? 'All requirements' : statusLabel(filter) }}
              </button>
            </div>
            <span>{{ filteredRequirements.length }} records</span>
          </div>
          <article class="panel table-panel full-panel">
            <div class="table-wrap">
              <table>
                <thead><tr><th>Client</th><th>Required document</th><th>Period</th><th>Due date</th><th>Status</th><th>Reminders</th><th></th></tr></thead>
                <tbody>
                  <tr v-for="requirement in filteredRequirements" :key="requirement.id">
                    <td><div class="client-cell"><span>{{ requirement.client_name.slice(0, 2).toUpperCase() }}</span><p><strong>{{ requirement.client_name }}</strong><small>{{ requirement.client_email }}</small></p></div></td>
                    <td><strong>{{ documentLabel(requirement.document_type) }}</strong></td>
                    <td>{{ requirement.period }}</td>
                    <td>{{ formatDate(requirement.due_date) }}</td>
                    <td><span class="status-pill" :class="statusClass(requirement.status)">{{ statusLabel(requirement.status) }}</span></td>
                    <td>{{ requirement.reminder_count }}</td>
                    <td><div class="row-actions"><button class="button tiny ghost" @click="openUpload(requirement)"><Upload :size="14" /> Upload</button><button v-if="requirement.status !== 'received'" class="icon-button" title="Send reminder" :disabled="mutating" @click="remind(requirement)"><Send :size="15" /></button></div></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </template>

        <template v-else-if="selectedView === 'documents'">
          <div class="filterbar">
            <div class="filter-tabs">
              <button v-for="filter in ['all', 'needs_review', 'ready', 'approved', 'rejected']" :key="filter" :class="{ active: statusFilter === filter }" @click="statusFilter = filter">
                {{ filter === 'all' ? 'All documents' : statusLabel(filter) }}
              </button>
            </div>
            <span>{{ reviewDocuments.length }} awaiting decisions</span>
          </div>
          <div class="document-grid">
            <article v-for="document in filteredDocuments" :key="document.id" class="document-card" @click="openReview(document)">
              <div class="document-preview">
                <span class="file-extension">{{ document.original_filename.split('.').pop()?.toUpperCase() }}</span>
                <FileSearch :size="34" />
                <div class="confidence-badge">{{ Math.round(document.confidence * 100) }}% confidence</div>
              </div>
              <div class="document-card-body">
                <div><span class="status-pill" :class="statusClass(document.status)">{{ statusLabel(document.status) }}</span><small>{{ formatDateTime(document.created_at) }}</small></div>
                <h3>{{ document.original_filename }}</h3>
                <p>{{ document.client_name }} · {{ documentLabel(document.document_type) }}</p>
                <button class="text-button">Inspect extraction <ChevronRight :size="15" /></button>
              </div>
            </article>
          </div>
        </template>

        <template v-else-if="selectedView === 'clients'">
          <div class="client-grid">
            <article v-for="client in clients" :key="client.id" class="client-card">
              <div class="client-card-head"><div class="large-avatar">{{ client.name.slice(0, 2).toUpperCase() }}</div><span class="status-pill status-received">Active</span></div>
              <p class="eyebrow">{{ client.industry }}</p>
              <h3>{{ client.name }}</h3>
              <p class="muted">{{ client.email }}</p>
              <div class="progress-row"><span><strong>{{ client.completion_rate }}%</strong> complete</span><span>{{ client.requirement_count }} requirements</span></div>
              <div class="progress-track"><i :style="{ width: `${client.completion_rate}%` }"></i></div>
              <button class="button ghost full" @click="navigate('requirements')">View collections <ChevronRight :size="15" /></button>
            </article>
          </div>
        </template>

        <template v-else-if="selectedView === 'activity'">
          <article class="panel audit-panel">
            <div class="audit-summary">
              <div><ShieldCheck :size="28" /><p><strong>Accountable by default</strong><span>Every upload, decision, requirement, and reminder is recorded with an actor and timestamp.</span></p></div>
              <span>{{ activity.length }} recent events</span>
            </div>
            <div class="timeline audit-timeline">
              <div v-for="entry in activity" :key="entry.id" class="timeline-item">
                <span><component :is="actionIcon(entry.action)" :size="17" /></span>
                <p><strong>{{ entry.detail }}</strong><small>{{ entry.actor }} · {{ formatDateTime(entry.created_at) }}</small></p>
                <code>{{ entry.action }}</code>
              </div>
            </div>
          </article>
        </template>
      </section>
    </main>

    <div v-if="modal" class="modal-backdrop" @mousedown.self="modal = null">
      <section v-if="modal === 'upload'" class="modal-card upload-modal">
        <div class="modal-heading"><div><p class="eyebrow">Document intake</p><h2>Upload a document</h2><p>The file is hashed, parsed, classified, and routed for review.</p></div><button class="icon-button" @click="modal = null"><X :size="19" /></button></div>
        <form @submit.prevent="submitUpload">
          <label>Client<select v-model.number="uploadForm.client_id" required><option v-for="client in clients" :key="client.id" :value="client.id">{{ client.name }}</option></select></label>
          <label>Match requirement<select v-model.number="uploadForm.requirement_id"><option :value="undefined">Auto-match from extracted metadata</option><option v-for="requirement in requirements.filter((item) => item.client_id === uploadForm.client_id && item.status !== 'received')" :key="requirement.id" :value="requirement.id">{{ documentLabel(requirement.document_type) }} · {{ requirement.period }}</option></select></label>
          <label class="dropzone"><input type="file" accept=".pdf,.docx,.txt,.csv,.json,.png,.jpg,.jpeg" required @change="uploadForm.file = ($event.target as HTMLInputElement).files?.[0] || null" /><Upload :size="26" /><strong>{{ uploadForm.file?.name || 'Choose a document' }}</strong><span>PDF, DOCX, TXT, CSV, JSON or image · up to 10 MB</span></label>
          <div class="modal-actions"><button type="button" class="button ghost" @click="modal = null">Cancel</button><button class="button primary" :disabled="mutating || !uploadForm.file"><Loader2 v-if="mutating" :size="16" class="spinning" /><Upload v-else :size="16" /> Process document</button></div>
        </form>
      </section>

      <section v-else-if="modal === 'requirement'" class="modal-card">
        <div class="modal-heading"><div><p class="eyebrow">Collection rule</p><h2>New requirement</h2><p>Define exactly what the client must provide and when.</p></div><button class="icon-button" @click="modal = null"><X :size="19" /></button></div>
        <form class="form-grid" @submit.prevent="submitRequirement">
          <label class="full-span">Client<select v-model.number="requirementForm.client_id" required><option v-for="client in clients" :key="client.id" :value="client.id">{{ client.name }}</option></select></label>
          <label>Period<input v-model="requirementForm.period" type="month" required /></label>
          <label>Due date<input v-model="requirementForm.due_date" type="date" required /></label>
          <label class="full-span">Document type<select v-model="requirementForm.document_type" required><option v-for="(label, key) in documentTypes" v-show="key !== 'unknown'" :key="key" :value="key">{{ label }}</option></select></label>
          <div class="modal-actions full-span"><button type="button" class="button ghost" @click="modal = null">Cancel</button><button class="button primary" :disabled="mutating"><Plus :size="16" /> Create requirement</button></div>
        </form>
      </section>

      <section v-else-if="modal === 'client'" class="modal-card">
        <div class="modal-heading"><div><p class="eyebrow">Portfolio setup</p><h2>Add a client</h2><p>Create a clean home for future collection requirements.</p></div><button class="icon-button" @click="modal = null"><X :size="19" /></button></div>
        <form @submit.prevent="submitClient">
          <label>Company name<input v-model="clientForm.name" type="text" placeholder="Acme Advisory" required /></label>
          <label>Finance contact<input v-model="clientForm.email" type="email" placeholder="finance@acme.example" required /></label>
          <label>Industry<input v-model="clientForm.industry" type="text" required /></label>
          <div class="modal-actions"><button type="button" class="button ghost" @click="modal = null">Cancel</button><button class="button primary" :disabled="mutating"><UserPlus :size="16" /> Add client</button></div>
        </form>
      </section>

      <section v-else-if="modal === 'review' && selectedDocument" class="modal-card review-modal">
        <div class="modal-heading"><div><p class="eyebrow">Human verification</p><h2>{{ selectedDocument.original_filename }}</h2><p>{{ selectedDocument.client_name }} · {{ documentLabel(selectedDocument.document_type) }}</p></div><button class="icon-button" @click="modal = null"><X :size="19" /></button></div>
        <div class="review-score"><div class="score-orb" :class="{ caution: selectedDocument.confidence < 0.8 }">{{ Math.round(selectedDocument.confidence * 100) }}<small>%</small></div><p><strong>Extraction confidence</strong><span>{{ selectedDocument.confidence >= 0.8 ? 'The document is ready for verification.' : 'Low-confidence fields require close inspection.' }}</span></p><span class="status-pill" :class="statusClass(selectedDocument.status)">{{ statusLabel(selectedDocument.status) }}</span></div>
        <div class="review-grid">
          <div><p class="eyebrow">Extracted fields</p><dl><template v-for="(value, key) in selectedDocument.extracted_data.fields" :key="key"><dt>{{ String(key).replaceAll('_', ' ') }}</dt><dd>{{ value }}</dd></template><template v-if="!Object.keys(selectedDocument.extracted_data.fields || {}).length"><dt>Result</dt><dd>No structured fields were accepted.</dd></template></dl></div>
          <div><p class="eyebrow">Routing metadata</p><dl><dt>Document type</dt><dd>{{ documentLabel(selectedDocument.document_type) }}</dd><dt>Period</dt><dd>{{ selectedDocument.period || 'Not detected' }}</dd><dt>File size</dt><dd>{{ formatBytes(selectedDocument.size_bytes) }}</dd><dt>Method</dt><dd>{{ selectedDocument.extracted_data.extraction_method || 'deterministic' }}</dd></dl></div>
        </div>
        <div v-if="selectedDocument.extracted_data.warnings?.length" class="warning-box"><CircleAlert :size="18" /><div><strong>Review warnings</strong><p v-for="warning in selectedDocument.extracted_data.warnings" :key="warning">{{ warning }}</p></div></div>
        <div v-if="['needs_review', 'ready'].includes(selectedDocument.status)" class="modal-actions"><button class="button danger" :disabled="mutating" @click="review('reject')"><XCircle :size="16" /> Reject</button><button class="button primary" :disabled="mutating" @click="review('approve')"><Check :size="16" /> Approve & match</button></div>
        <div v-else class="review-complete"><CheckCircle2 :size="18" /> Review completed · {{ statusLabel(selectedDocument.status) }}</div>
      </section>
    </div>
  </div>
</template>
