# Krystal Le Agent (CPA Firm Internal AI) — Implementation Spec for Claude Code Opus 4.5
**Version:** 1.1
**Date:** 2026-01-10
**Owner:** Krystal Le CPA (Internal)
**Scope:** Internal-only assistant for tax season workflow acceleration (1040 + business returns)

---

## Implementation Status

| Milestone | Status | Completed Date | Notes |
|-----------|--------|----------------|-------|
| **M1 (Core)** | ✅ Complete | 2026-01-10 | Full ingestion pipeline, hybrid search, chat with citations |
| **M2 (NAS Sync)** | ✅ Complete | 2026-01-11 | NAS sync agent, folder parsing, admin approval queue |
| **M3 (Artifacts)** | ✅ Complete | 2026-01-10 | Template renderer, 6 Jinja2 templates, artifact storage, IntakeAgent |
| **M4 (Extraction)** | ✅ Complete | 2026-01-11 | ExtractionAgent, NoticeAgent, QCAgent, auto-extraction worker |

### M1 Completion Details
- Docker Compose infrastructure (Postgres+pgvector, Redis, MinIO) ✓
- Document upload API with automatic ingestion trigger ✓
- Full ingestion pipeline: extract → OCR fallback → canonicalize → chunk → embed ✓
- Hybrid search: pgvector (0.7) + tsvector (0.3) combined scoring ✓
- Chat endpoint with intent classification and document citations ✓
- SSE streaming with citations event ✓

### M2 Completion Details
- NAS Sync Agent service with real-time filesystem monitoring ✓
- FolderParser: Extract client/case/document info from NAS paths ✓
- LnkParser: Parse Windows shortcuts for client→business relationships ✓
- NASWatcher: Watchdog-based monitoring with 2-second debouncing ✓
- FullScanner: Initial backfill of existing NAS files ✓
- Admin approval queue for new clients/cases (auto-approve after 4h) ✓
- Client relationships table (individual↔business links from .lnk files) ✓
- Soft delete with 90-day retention ✓
- Daily digest email sender ✓
- API endpoints: file-arrived, file-deleted, heartbeat, sync-queue, relationship, sync-status ✓
- Admin UI: Sync queue management page ✓
- 32 unit tests for parser and lnk_parser ✓

### M3 Completion Details
- Template rendering service with Jinja2 and custom filters ✓
- 6 production templates: missing_docs_email, organizer_checklist, notice_response, qc_memo, extraction_summary, metadata registry ✓
- Template context service for database entity preparation ✓
- IntakeAgent subagent for LLM-powered document analysis ✓
- MCP servers for template operations and artifact storage ✓
- Frontend artifact viewer components ✓
- Artifact storage in PostgreSQL ✓

### M4 Completion Details
- ExtractionAgent for W-2/1099/K-1 structured data extraction ✓
- Type-specific system prompts with IRS box mappings ✓
- Anomaly detection (negative values, tax > wages, missing fields) ✓
- Confidence scoring (HIGH/MEDIUM/LOW) with needs_review flags ✓
- NoticeAgent for IRS notice analysis and response drafting ✓
- Notice type detection (CP2000, CP501, CP504, LT11, etc.) ✓
- QCAgent for quality control review memos ✓
- Individual and business return checklists ✓
- Auto-extraction Celery worker task ✓
- Orchestrator routing for extraction, notice, qc intents ✓

### Storage Abstraction Implementation (Bonus)
- Abstract StorageBackend interface ✓
- Filesystem backend for NAS deployment ✓
- Database migration: s3_key → storage_key ✓
- Updated document upload/download routes ✓
- Worker ingestion pipeline updated ✓

### NAS Deployment Infrastructure (Bonus)
- docker-compose.nas.yml for Synology Container Station ✓
- Dockerfiles for API, Worker, Web services ✓
- Direct filesystem mounting to `/volume1/LeCPA/ClientFiles/` ✓
- Production-ready configuration with health checks ✓

---

## 0) Goals (What "done" looks like)
Build an internal web app ("Le CPA Agent") that:
- Lets staff chat with a firm assistant that can **search and cite** internal firm guidance + client documents.
- Produces **artifacts**: missing-docs email drafts, organizer checklists, IRS notice response drafts, QC memos.
- Ingests documents from the firm's **NAS** via real-time filesystem monitoring, and indexes them for retrieval.
- Uses **Claude Opus 4.5 as default model** everywhere, but can switch models/providers via config without refactoring.
- Uses **OCR as fallback-only** for scanned/image PDFs.

Non-goals (v1):
- Drake UI automation (use file exports/imports and a "bridge" approach).

---

## 1) High-Level Architecture
### Services
1) **Web UI (Next.js)**
- Chat interface (streaming responses)
- Case Workspace (per client/year/return/notice)
- Citations viewer (shows which doc/page/chunk supported an answer)
- Artifact viewer (email drafts, checklists, memos)

2) **API / Orchestrator (FastAPI)**
- Auth + user management
- Case/document metadata + permissions (v1: all staff access)
- Agent orchestration + tool calling
- Audit logs of document access and tool calls
- Webhook receiver endpoints (optional; Zapier)

3) **Worker (Celery + Redis)**
- Document ingestion pipeline
- OCR fallback pipeline
- Embeddings + chunking pipeline
- Scheduled refresh jobs (optional: authoritative tax sources snapshots)
- (Optional) QC batch jobs

4) **NAS Sync Agent (Docker container)**
- Watches NAS folders for new/updated files via watchdog
- Notifies API to ingest via `/ingest/file-arrived`
- Maintains file hash (SHA256) for deduplication
- Queues new clients/cases for admin approval

### Data Stores
- **Postgres** (cases, docs metadata, audit logs)
- **pgvector** (embeddings)
- **S3/MinIO** (raw files + extracted text artifacts)
- **Redis** (queue + short-lived state)

---

## 2) Model Strategy (Default Claude, Swappable)
### Requirements
- All LLM calls must go through a **ModelRouter** layer.
- Default model = **Claude Opus 4.5**.
- Ability to switch provider/model by editing `config/model_router.yaml`.

### `config/model_router.yaml`
```yaml
default_provider: anthropic
default_model: claude-opus-4-5

routes:
  orchestrator: { provider: anthropic, model: claude-opus-4-5 }
  drafting:     { provider: anthropic, model: claude-opus-4-5 }
  extraction:   { provider: anthropic, model: claude-opus-4-5 }
  qc:           { provider: anthropic, model: claude-opus-4-5 }
  research:     { provider: anthropic, model: claude-opus-4-5 }

fallbacks:
  - provider: anthropic
    model: claude-sonnet-4-5
```

### Env Vars
- `ANTHROPIC_API_KEY`
- (Optional future) `OPENAI_API_KEY`

---

## 3) OCR (Fallback Only)
### Requirements
- Default: **NO OCR unless needed**.
- OCR triggers only when extracted text is too small / likely image-only PDF.

### `config/ocr.yaml`
```yaml
enabled: true
mode: fallback_only
min_chars_per_page: 200
min_text_ratio: 0.001

engine: tesseract
tesseract:
  lang: eng
  psm: 6
  oem: 1
  dpi: 300
```

### Ingestion Logic
1) Extract text with normal PDF extraction (pymupdf or pypdf).
2) Compute:
   - `avg_chars_per_page`
   - `text_ratio` (chars / file_bytes)
3) If below thresholds -> OCR each page image
4) Store OCR text with flags: `is_ocr=true`, page refs, confidence where available.

---

## 4) Document Access: NAS Filesystem
### Approach
- Mount the firm's NAS directly to the Docker container or host machine.
- Sync Agent monitors the NAS filesystem for changes using watchdog.
- Files are processed in-place (no S3 upload needed for NAS deployment).

### NAS Folder Structure
```
/volume1/LeCPA/ClientFiles/
├── 1001_Toh, Wei Ming/           # Individual client (1xxx)
│   ├── 2024/                     # Year folder → Case
│   │   ├── 2024 W-2.pdf
│   │   └── 2024 K-1s/
│   ├── Permanent/                # Evergreen documents
│   ├── Tax Notice/               # IRS notices
│   └── 2010_Business.lnk         # Link to related business
├── 2010_Sim Sim Realty LLC/      # Business entity (2xxx)
│   ├── 2024/
│   └── Permanent/
```

### Folder Parsing Rules
Configured in `services/nas-sync-agent/config.yaml`:
```yaml
parsing:
  client_patterns:
    - pattern: "^(?P<code>1\\d{3})_(?P<name>.+)$"
      type: individual
    - pattern: "^(?P<code>2\\d{3})_(?P<name>.+)$"
      type: business

  year_pattern: "^(?P<year>20\\d{2})$"

  special_folders:
    - folder: Permanent
      tag: permanent
      is_permanent: true
    - folder: Tax Notice
      tag: tax_notice
    - folder: Tax Transcript
      tag: transcript

  skip_patterns:
    - "*.7z"
    - "*.zip"
    - "*.lnk"
    - ".DS_Store"
    - "~$*"

  document_tags:
    - pattern: "(?i)w-?2"
      tag: W2
    - pattern: "(?i)1099"
      tag: "1099"
    - pattern: "(?i)k-?1|k1p|k1s"
      tag: K1
    - pattern: "(?i)notice|cp\\s?\\d+|lt\\s?\\d+"
      tag: IRS_NOTICE
```

---

## 5) NAS Sync Agent
### Service Location
`services/nas-sync-agent/`

### Components
- **FolderParser**: Extracts client/case/document info from NAS paths
- **LnkParser**: Parses Windows `.lnk` shortcuts for client relationships
- **NASWatcher**: Real-time filesystem monitoring with watchdog
- **FullScanner**: Initial backfill of existing files
- **APIClient**: HTTP client for API communication with retry logic
- **DigestSender**: Daily summary email sender

### CLI Commands
```bash
nas-sync watch      # Start real-time filesystem watcher
nas-sync scan       # Full scan for initial backfill
nas-sync digest     # Send daily digest email manually
nas-sync init_config # Generate default config file
nas-sync validate   # Validate configuration
```

### API Endpoints
- `POST /ingest/file-arrived` - New/modified file notification
- `POST /ingest/file-deleted` - File deletion (soft delete)
- `POST /ingest/heartbeat` - Agent health check
- `GET /ingest/sync-queue` - List pending approvals
- `POST /ingest/sync-queue/{id}/approve` - Approve client/case
- `POST /ingest/sync-queue/{id}/reject` - Reject item
- `POST /ingest/relationship` - Record client relationship
- `GET /ingest/sync-status` - Dashboard statistics

### Admin Approval Workflow
New clients/cases detected on NAS are queued for admin approval:
- Default auto-approve after 4 hours (configurable)
- Admin UI shows pending items with approve/reject buttons
- Client relationships from `.lnk` files auto-created

### Tech Stack
- Python 3.11+
- `watchdog` for filesystem events
- `httpx` + `tenacity` for API calls with retry
- `structlog` for structured logging
- `typer` for CLI
- Run as Docker container with NAS volume mount

### Failure Handling
- Debounced events (2-second window) to handle rapid changes
- Exponential backoff on API failures
- Soft delete with 90-day retention
- Never modify NAS contents (read-only access)

---

## 6) Ingestion Pipeline (Worker)
### Steps
1) Receive `file-arrived` event
2) Store raw file in object storage
3) Extract text:
   - pdf/docx/xlsx handlers
4) OCR fallback if needed
5) Chunk text (e.g., 800–1200 tokens with overlap)
6) Embed chunks -> store in pgvector
7) Create citations mapping:
   - doc_id, chunk_id, page range, is_ocr flag

### Libraries
- PDF: `pymupdf` or `pypdf`
- DOCX: `python-docx`
- XLSX: `openpyxl` (extract sheet values as text)
- OCR: `pytesseract` + `poppler` (pdftoppm) for images

---

## 7) Agent System (Orchestrator + Subagents)
### Guardrails (Hard Rules)
- No tax-law claim without citations (internal doc or authoritative snapshot)
- Never fabricate numbers; must be from documents or explicit user inputs
- Always output “Needed info” section when facts are missing
- Log doc access + tool usage in audit table

### Agents
1) **Orchestrator**
- Classifies intent: question / drafting / extraction / notice / QC / intake
- Calls the right subagent
- Enforces guardrails + format

2) **Firm Knowledge Agent**
- RAG over internal SOPs, templates, prior memos

3) **Tax Law Research Agent**
- Uses authoritative snapshot library (optional v1; recommended v1.1)
- Returns citations

4) **Intake / Missing Docs Agent**
- Generates checklist for 1040/business
- Generates client email draft

5) **Document Extraction Agent**
- Extract structured fields into JSON for W-2/1099/K-1/etc
- Outputs confidence + exceptions list

6) **IRS Notice Response Agent**
- Draft response letter + attachment list + “Needed info”

7) **QC Agent**
- Runs a firm checklist + flags anomalies and missing items

---

## 8) MCP Tool Layer (Servers)
Implement MCP servers so agents use tools consistently.

### Servers (v1)
1) **mcp_kb_server**
- `search_docs(query, filters)`
- `get_doc(doc_id)`
- `list_templates(type)`
- `render_template(template_id, vars)`

2) **mcp_case_server**
- `create_case(client_code, year, type)`
- `attach_document(case_id, doc_id, tags)`
- `get_case_summary(case_id)`
- `write_artifact(case_id, kind, content)`

3) **mcp_drake_bridge_server** (v1.1)
- `import_drake_export(csv_path)`
- `get_client_index(query)`
- `generate_drake_packet(case_id)` -> exports artifacts for Drake cabinet

4) **mcp_law_server** (v1.1)
- `search_authoritative(query)`
- `fetch_and_snapshot(url)`

---

## 9) Repo Layout
```text
lecpa-agent/
  apps/
    web/                        # Next.js UI
    api/                        # FastAPI orchestrator
  services/
    worker/                     # Celery ingestion + OCR + embeddings
    nas-sync-agent/             # NAS filesystem sync agent
    mcp-kb-server/
    mcp-case-server/
    mcp-drake-bridge-server/    # optional v1.1
    mcp-law-server/             # optional v1.1
  packages/
    shared/                     # schemas, typed contracts
  infra/
    docker-compose.yml
    docker-compose.nas.yml      # NAS deployment config
    terraform/                  # optional
  config/
    model_router.yaml
    ocr.yaml
    folder_rules.yaml
  docs/
    architecture.md
    runbooks.md
    security.md
```

---

## 10) Security + Audit (v1 baseline)
- Internal-only auth (Google Workspace OIDC preferred)
- All staff access in v1 (simple RBAC later)
- Store an **audit_log** record for:
  - doc opened
  - search query executed
  - artifact exported
- Default UI redaction for SSNs (mask all but last 4)

---

## 11) Acceptance Tests (Must Pass)
1) **NAS file -> searchable**
- Drop a PDF into a client folder on NAS
- Within 1 minute: doc appears in Case UI and can be searched

2) **Chat with citations**
- Ask: "Summarize this client's W-2 and 1099s"
- Response includes citations pointing to doc pages/chunks

3) **Missing docs email**
- Agent generates a client email requesting missing items
- Saved as an artifact under the case

4) **OCR fallback**
- Upload a scanned notice PDF (image-only)
- System runs OCR automatically and answer cites OCR pages

5) **Admin approval workflow**
- Create new client folder on NAS
- Item appears in admin sync queue
- Approve/reject works correctly

6) **Client relationships**
- Add `.lnk` shortcut to individual client folder pointing to business
- Relationship auto-created in database

---

## 12) Implementation Milestones

### M1 (Core) — ✅ COMPLETE
- [x] docker-compose runs: api/web/worker/postgres/redis/minio
- [x] upload docs manually + ingest + RAG chat + citations
- [x] Hybrid search with pgvector + tsvector
- [x] Chat endpoint with intent classification
- [x] SSE streaming with citations

### M2 (NAS Sync) — ✅ COMPLETE
- [x] NAS sync agent with watchdog filesystem monitoring
- [x] Folder parser for client/case/document extraction
- [x] LNK parser for client relationships
- [x] Admin approval queue with auto-approve
- [x] API endpoints for file events and queue management
- [x] Admin UI for sync queue management
- [x] Daily digest email sender
- [x] 32 unit tests passing

### M3 (Artifacts) — ✅ COMPLETE
- [x] templates + renderer + save artifacts to cases
- [x] Missing docs email generation
- [x] Organizer checklist generation
- [x] IntakeAgent for LLM-powered analysis

### M4 (Extraction + Notice) — ✅ COMPLETE
- [x] W-2/1099/K-1 extraction with confidence scoring
- [x] Notice response drafting (CP2000, CP501, etc.)
- [x] QC memo generation with checklists
- [x] Auto-extraction worker task

---

## 13) Notes / Assumptions
- NAS is accessible via Docker volume mount or direct filesystem access
- Client folders follow naming convention: `{code}_{name}` (1xxx=individual, 2xxx=business)
- Year folders represent tax cases (e.g., `2024/`)
- `.lnk` shortcuts indicate client relationships (individual→business)
- Drake integration is file-based (exports/imports), not UI automation

---

## Appendix A — Suggested Tech Dependencies
### Backend
- FastAPI, uvicorn
- SQLAlchemy + Alembic
- Celery + Redis
- pgvector
- boto3
- tenacity
- structlog

### Parsing/OCR
- pymupdf (fitz) or pypdf
- python-docx
- openpyxl
- pytesseract
- poppler utils (pdftoppm)

### Frontend
- Next.js, Tailwind
- SSE/WebSocket streaming

---
