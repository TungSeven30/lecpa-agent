# Krystal Le Agent (CPA Firm Internal AI) — Implementation Spec for Claude Code Opus 4.5
**Version:** 1.0  
**Date:** 2026-01-09  
**Owner:** Krystal Le CPA (Internal)  
**Scope:** Internal-only assistant for tax season workflow acceleration (1040 + business returns)

---

## 0) Goals (What “done” looks like)
Build an internal web app (“Krystal Le Agent”) that:
- Lets staff chat with a firm assistant that can **search and cite** internal firm guidance + client documents.
- Produces **artifacts**: missing-docs email drafts, organizer checklists, IRS notice response drafts, QC memos.
- Ingests documents from **TaxDome Document system** via **TaxDome Drive** (virtual drive), and indexes them for retrieval.
- Uses **Claude Opus 4.5 as default model** everywhere, but can switch models/providers via config without refactoring.
- Uses **OCR as fallback-only** for scanned/image PDFs.

Non-goals (v1):
- Full TaxDome automation via API (assume no public API; use Drive + optional Zapier webhooks).
- Drake UI automation (use file exports/imports and a “bridge” approach).

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

4) **TaxDome Drive Sync Agent (Windows service)**
- Watches TaxDome Drive folders for new/updated files
- Mirrors to S3/MinIO + notifies API to ingest
- Maintains local state to avoid duplicates (SHA256)

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

## 4) Document Access: TaxDome Drive (No Dropbox)
### Approach
- Install **TaxDome Drive** on a dedicated Windows machine (physical or hosted).
- Sync Agent mirrors TaxDome Drive content into our own storage for indexing.

### Folder Parsing
TaxDome folders appear like: `TH4 10 tax Returns - Hioki`, `MM7 1602 Martinez LLC`, etc.

#### `config/folder_rules.yaml` (example)
```yaml
source: taxdome_drive
roots:
  - "X:\TaxDome Drive\Clients"  # replace at install or auto-detect

client_folder:
  pattern: "^(?P<client_code>[A-Z0-9]{2,5})\s+(?P<client_name>.+)$"

case_detection:
  - name: "tax_year_folder"
    pattern: "^(?P<year>20\d{2})$"
    case_type: "tax_return"

doc_tags:
  - match: "(?i)w-?2"
    tag: "W2"
  - match: "(?i)1099"
    tag: "1099"
  - match: "(?i)k-?1"
    tag: "K1"
  - match: "(?i)notice|cp\s?\d+|lt\s?\d+"
    tag: "IRS_NOTICE"
```

### Drive Root Auto-Detect (Setup)
If the drive letter/path is unknown, implement a setup step:
- Scan mounted drives for directory name containing “TaxDome Drive”
- Save discovered root into config file or DB settings

---

## 5) TaxDome Sync Agent (Windows)
### Service Location
`services/taxdome-sync-agent/`

### Responsibilities
- Monitor folder tree under TaxDome Drive root(s)
- Detect new/changed files using:
  - last modified time + file size
  - SHA256 hash (for definitive de-dup)
- Upload file to S3/MinIO with stable key:
  - `taxdome/{client_code}/{year}/{relative_path}/{filename}`
- Notify API: `POST /ingest/file-arrived`
- Keep a local sqlite db `sync_state.db`:
  - filepath, modified_time, size, sha256, last_uploaded_at, last_seen_at

### Tech Stack
- Python 3.11+
- `watchdog` (filesystem events) + periodic scan fallback
- `boto3` (S3)
- `requests` (API notify)
- Run as:
  - Windows Service (preferred) OR
  - scheduled task + long-running process

### Failure Handling
- Retries with backoff
- If upload fails: queue and retry
- Never delete/modify the TaxDome Drive contents

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

3) **mcp_taxdome_drive_server**
- Primarily for internal abstraction; actual access via sync agent + DB.
- `list_client_folders()`
- `resolve_path_to_client(path)`

4) **mcp_drake_bridge_server** (v1.1)
- `import_drake_export(csv_path)`
- `get_client_index(query)`
- `generate_drake_packet(case_id)` -> exports artifacts for Drake cabinet

5) **mcp_law_server** (v1.1)
- `search_authoritative(query)`
- `fetch_and_snapshot(url)`

---

## 9) Repo Layout
```text
krystal-le-agent/
  apps/
    web/                        # Next.js UI
    api/                        # FastAPI orchestrator
  services/
    worker/                     # Celery ingestion + OCR + embeddings
    taxdome-sync-agent/         # Windows sync agent for TaxDome Drive
    mcp-kb-server/
    mcp-case-server/
    mcp-drake-bridge-server/    # optional v1.1
    mcp-law-server/             # optional v1.1
  packages/
    shared/                     # schemas, typed contracts
  infra/
    docker-compose.yml
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
1) **TaxDome Drive file -> searchable**
- Drop a PDF into a client folder in TaxDome Drive
- Within N minutes: doc appears in Case UI and can be searched

2) **Chat with citations**
- Ask: “Summarize this client’s W-2 and 1099s”
- Response includes citations pointing to doc pages/chunks

3) **Missing docs email**
- Agent generates a client email requesting missing items
- Saved as an artifact under the case

4) **OCR fallback**
- Upload a scanned notice PDF (image-only)
- System runs OCR automatically and answer cites OCR pages

---

## 12) Implementation Milestones
### M1 (Core)
- docker-compose runs: api/web/worker/postgres/redis/minio
- upload docs manually + ingest + RAG chat + citations

### M2 (TaxDome Drive ingestion)
- Windows sync agent + ingestion trigger + folder mapping

### M3 (Artifacts)
- templates + renderer + save artifacts to cases

### M4 (Extraction + Notice)
- basic W-2/1099 extraction JSON
- notice response draft

---

## 13) Notes / Assumptions to Verify
- TaxDome Drive is available and installed on a dedicated Windows machine
- TaxDome public API availability is limited; plan assumes Drive-based ingestion
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
