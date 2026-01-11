# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Le CPA Agent is an internal AI assistant for a CPA firm, designed to accelerate tax season workflows (1040 + business returns). It provides RAG-powered chat with document citations, generates artifacts (email drafts, checklists, IRS notice responses), and ingests documents from TaxDome Drive.

See `docs/implementation-spec.md` for the full implementation specification.

## Current Status

| Milestone | Status | Description |
|-----------|--------|-------------|
| **M1 (Core)** | ✅ Complete | Docker infra, document ingestion, hybrid search, chat with citations |
| **M2 (TaxDome)** | 🔲 Not Started | Windows sync agent, folder mapping |
| **M3 (Artifacts)** | ✅ Complete | Template renderer, 6 Jinja2 templates, artifact storage, IntakeAgent |
| **M4 (Extraction)** | ✅ Complete | ExtractionAgent, NoticeAgent, QCAgent, auto-extraction worker |

## Architecture

```
apps/
  web/                    # Next.js 14 frontend (chat UI, case workspace, citations viewer)
  api/                    # FastAPI backend (orchestrator, auth, case management)
services/
  worker/                 # Celery workers (ingestion, OCR, embeddings)
  taxdome-sync-agent/     # Windows service syncing TaxDome Drive to S3/MinIO
  mcp-kb-server/          # MCP server for document search/templates
  mcp-case-server/        # MCP server for case management
packages/
  shared/                 # Shared Pydantic schemas and typed contracts
config/
  model_router.yaml       # LLM provider/model configuration
  embeddings.yaml         # Embedding model settings (BGE models)
  ocr.yaml                # OCR fallback settings
  folder_rules.yaml       # TaxDome folder parsing rules
  templates/*.jinja2      # Jinja2 templates for artifacts
```

**Data Stores:** Postgres (cases, docs, audit), pgvector (embeddings), S3/MinIO or Filesystem/NAS (files), Redis (queue)

**Package Management:** Python uses `uv` workspace (see `pyproject.toml` for members), Next.js uses `pnpm`

## Development Commands

```bash
# Environment setup (Python - uv workspace)
uv sync                                    # Install all workspace dependencies
source .venv/bin/activate                  # Activate venv

# Environment setup (Next.js - pnpm workspace)
cd apps/web && pnpm install

# Run infrastructure
docker compose -f infra/docker-compose.yml up -d

# Run API server
cd apps/api && uvicorn main:app --reload --port 8000

# Run Celery worker (with all queues)
cd services/worker && celery -A main worker --loglevel=info -Q ingest,extract,ocr,embed,field_extraction

# Run Next.js dev server
cd apps/web && pnpm dev

# Testing
pytest                                     # Run all tests
pytest tests/unit/test_foo.py -v           # Run single test file
pytest -k "test_name"                      # Run tests matching pattern
pytest tests/e2e/                          # Run E2E tests only

# Code quality
ruff check .                               # Lint
ruff format .                              # Format
mypy apps/api services/worker packages/    # Type check

# Database migrations
cd apps/api && alembic upgrade head        # Apply migrations
cd apps/api && alembic revision --autogenerate -m "description"  # Create migration
```

## Key Patterns

### ModelRouter
All LLM calls go through `ModelRouter` (`apps/api/services/model_router.py`) which reads `config/model_router.yaml`. Default is Claude Opus 4.5. Routes defined for: orchestrator, drafting, extraction, qc, research.

### EmbeddingProvider
Local embeddings via sentence-transformers (BGE models). Config in `config/embeddings.yaml`:
- Default: `BAAI/bge-small-en-v1.5` (384 dimensions)
- Query prefix required for BGE: `"Represent this sentence for searching relevant passages: "`

### Document Ingestion Pipeline (`services/worker/tasks/ingest.py`)
Status transitions: `pending → extracting → canonicalizing → chunking → embedding → ready → failed`

1. Download from storage backend
2. Extract text (pymupdf/python-docx/openpyxl via `tasks/extract.py`)
3. OCR fallback if `avg_chars_per_page < 200` or `text_ratio < 0.001` (`tasks/ocr.py`)
4. Canonicalize: Remove headers/footers, collapse whitespace (`tasks/canonicalize.py`)
5. Chunk (800–1200 tokens) and embed (`tasks/embed.py`)
6. Store chunks to pgvector + tsvector
7. Auto-extract if document tagged W2/1099/K1 (`tasks/field_extraction.py`)

### Hybrid Search (`apps/api/services/search.py`)
- pgvector for semantic similarity (cosine distance)
- Postgres tsvector + GIN index for full-text search
- Combined: `final_score = vector_score * 0.7 + fts_score * 0.3`

### Agent System (`apps/api/services/agents/`)
- **Orchestrator**: Classifies intent → routes to subagent → enforces guardrails
- **Intents**: question, drafting, extraction, notice, qc, intake
- **Subagents**:
  - `IntakeAgent`: Missing docs emails, organizer checklists
  - `ExtractionAgent`: W-2/1099/K-1 structured data with confidence scoring
  - `NoticeAgent`: IRS notice analysis (CP2000, CP501, CP504, LT11) + response drafts
  - `QCAgent`: QC memos with individual/business checklists
- **Hard rules**: No tax claims without citations, no fabricated numbers, always output "Needed info" when facts missing

### Storage Backend (`apps/api/services/storage/`)
Abstract interface supporting:
- **Filesystem (NAS)**: Direct mount to `/volume1/LeCPA/ClientFiles/` or local path
- **S3/MinIO**: Object storage for cloud deployments
- Switch via `STORAGE_BACKEND` env var

### Artifact System
Template rendering via `TemplateRenderer` (`apps/api/services/template_renderer.py`):
- 6 Jinja2 templates in `config/templates/`
- Custom filters: `format_currency`, `mask_ssn`, `format_date`, `format_list`
- Metadata registry in `config/templates/metadata.yaml`

### API Routes (`apps/api/routers/`)
| Route | Description |
|-------|-------------|
| `/chat` | Chat endpoint (SSE streaming or JSON) |
| `/documents` | Document upload/download |
| `/cases` | Case CRUD |
| `/clients` | Client management |
| `/search` | Document search |
| `/artifacts` | Artifact management |

### Database Models (`apps/api/database/models.py`)
Core entities: `Client`, `Case`, `Document`, `DocumentChunk`, `Artifact`, `AuditLog`, `User`

## Testing

Test fixtures in `tests/conftest.py`:
- `project_root`, `golden_data_dir`, `config_dir` path fixtures
- `db_session` for database tests
- Sample documents in `tests/golden/` (W2, 1099, K1, IRS notice PDFs)

Test DB: `postgresql://lecpa:lecpa_dev@localhost:5432/lecpa_agent_test`

## Environment Variables

```
ANTHROPIC_API_KEY=       # Required for Claude models
DATABASE_URL=            # Postgres connection string
REDIS_URL=               # Redis connection string
CELERY_BROKER_URL=       # Celery broker (defaults to REDIS_URL)
S3_ENDPOINT=             # MinIO/S3 endpoint
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=               # Default: lecpa-documents
STORAGE_BACKEND=         # Storage type: filesystem or s3 (default: filesystem)
NAS_MOUNT_PATH=          # NAS mount path (for filesystem backend)
AUTO_EXTRACT_ENABLED=    # Enable auto-extraction for W2/1099/K1 documents (default: false)
```

## Domain-Specific Context

- **TaxDome folders** follow pattern: `{client_code} {client_name}` (e.g., `TH4 10 tax Returns - Hioki`)
- **Document tags** auto-detected: W2, 1099, K1, IRS_NOTICE
- **SSNs** must be masked in UI (show only last 4 digits)
- **Audit logging** required for: doc access, search queries, artifact exports
