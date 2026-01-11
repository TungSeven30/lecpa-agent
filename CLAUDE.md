# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Krystal Le Agent is an internal AI assistant for a CPA firm, designed to accelerate tax season workflows (1040 + business returns). It provides RAG-powered chat with document citations, generates artifacts (email drafts, checklists, IRS notice responses), and ingests documents from TaxDome Drive.

See `docs/implementation-spec.md` for the full implementation specification.

## Current Status

| Milestone | Status | Description |
|-----------|--------|-------------|
| **M1 (Core)** | ✅ Complete | Docker infra, document ingestion, hybrid search, chat with citations |
| **M2 (TaxDome)** | 🔲 Not Started | Windows sync agent, folder mapping |
| **M3 (Artifacts)** | ✅ Complete | Template renderer, 6 Jinja2 templates, artifact storage, IntakeAgent |
| **M4 (Extraction)** | 🔲 Not Started | W-2/1099 extraction, IRS notice response |

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

Storage Abstraction:
  apps/api/services/storage/
    base.py               # StorageBackend interface
    filesystem.py         # Filesystem backend (NAS)
    __init__.py           # Storage factory
```

**Data Stores:** Postgres (cases, docs, audit), pgvector (embeddings), S3/MinIO or Filesystem/NAS (files), Redis (queue)

**Package Management:** Python uses `uv` workspace, Next.js uses `pnpm`

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

# Run Celery worker
cd services/worker && celery -A main worker --loglevel=info

# Run Next.js dev server
cd apps/web && pnpm dev

# Testing
pytest                                     # Run all tests
pytest tests/test_foo.py -v                # Run single test file
pytest -k "test_name"                      # Run tests matching pattern
pytest tests/e2e/                          # Run E2E tests only

# Code quality
ruff check .                               # Lint
ruff format .                              # Format
mypy apps/api services/worker packages/    # Type check

# Database migrations
cd apps/api && alembic upgrade head        # Apply migrations
cd apps/api && alembic revision --autogenerate -m "description"  # Create migration

# Docker deployment (production)
docker-compose -f docker-compose.nas.yml up -d --build  # NAS deployment
docker-compose -f infra/docker-compose.yml up -d         # Local development
```

## Key Patterns

### ModelRouter
All LLM calls go through `ModelRouter` which reads `config/model_router.yaml`. Default is Claude Opus 4.5, swappable without code changes. Routes defined for: orchestrator, drafting, extraction, qc, research.

### EmbeddingProvider
Local embeddings via sentence-transformers (BGE models). Config in `config/embeddings.yaml`:
- Default: `BAAI/bge-small-en-v1.5` (384 dimensions)
- Query prefix required for BGE: `"Represent this sentence for searching relevant passages: "`
- Model name and dimension stored in DB for re-indexing support

### Document Ingestion Flow
1. TaxDome Sync Agent detects file → uploads to S3 → calls `POST /ingest/file-arrived`
2. Worker extracts text (pymupdf/python-docx/openpyxl)
3. OCR fallback triggers only if `avg_chars_per_page < 200` or `text_ratio < 0.001`
4. **Canonicalization**: Remove headers/footers, collapse whitespace, preserve page boundaries
5. Chunking: 800–1200 tokens with overlap
6. Chunks embedded to pgvector + tsvector (hybrid search) with citation mapping

### Document Processing Status
Documents track processing state: `pending → extracting → canonicalizing → chunking → embedding → ready → failed`

### Hybrid Search
- pgvector for semantic similarity
- Postgres tsvector + GIN index for full-text search
- Combined: `final_score = vector_score * 0.7 + fts_score * 0.3`

### Agent System
- **Orchestrator**: Routes intents to subagents, enforces guardrails
- **Subagents**: Firm Knowledge, Tax Law Research, Intake/Missing Docs, Document Extraction, IRS Notice Response, QC
- **Hard rules**: No tax claims without citations, no fabricated numbers, always output "Needed info" when facts missing

### MCP Servers
Agents use MCP tools via:
- **mcp_kb_server**: `search_docs`, `get_doc`, `list_templates`, `render_template`
- **mcp_case_server**: `create_case`, `attach_document`, `get_case_summary`, `write_artifact`

### Storage Backend
Configurable storage abstraction supporting multiple backends:
- **Filesystem (NAS)**: Direct mount to `/volume1/LeCPA/ClientFiles/` or local path
- **S3/MinIO**: Object storage for cloud deployments
- Switch backends via `STORAGE_BACKEND` environment variable
- Abstract interface in `apps/api/services/storage/base.py`
- Database uses `storage_key` (provider-agnostic) instead of `s3_key`

### Artifact System
Template rendering via `TemplateRenderer` service:
- 6 Jinja2 templates in `config/templates/`
- Custom filters: `format_currency`, `mask_ssn`, `format_date`, `format_list`
- Template metadata registry in `config/templates/metadata.yaml`
- Context preparation from database entities
- IntakeAgent for LLM-powered document analysis

## Testing

Test fixtures in `tests/conftest.py` provide:
- `project_root`, `golden_data_dir`, `config_dir` path fixtures
- `db_session` for database tests
- Sample documents in `tests/golden/` (W2, 1099, K1, IRS notice PDFs)

Test DB: PostgreSQL on `localhost:5432/lecpa_agent_test`

## Environment Variables

```
ANTHROPIC_API_KEY=       # Required for Claude models
DATABASE_URL=            # Postgres connection string
REDIS_URL=               # Redis connection string
S3_ENDPOINT=             # MinIO/S3 endpoint
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=               # Default: lecpa-documents
STORAGE_BACKEND=         # Storage type: filesystem or s3 (default: filesystem)
NAS_MOUNT_PATH=          # NAS mount path (for filesystem backend)
DEPLOYMENT_TYPE=         # Deployment: nas, cloud, or local
```

## Domain-Specific Context

- **TaxDome folders** follow pattern: `{client_code} {client_name}` (e.g., `TH4 10 tax Returns - Hioki`)
- **Document tags** auto-detected: W2, 1099, K1, IRS_NOTICE
- **SSNs** must be masked in UI (show only last 4 digits)
- **Audit logging** required for: doc access, search queries, artifact exports
