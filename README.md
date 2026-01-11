# Krystal Le Agent

Internal AI assistant for CPA firm tax season workflows.

## Features

- **RAG-Powered Chat**: Search and cite internal firm guidance + client documents
- **Document Ingestion**: Automatic processing of PDFs, DOCX, XLSX with OCR fallback
- **Hybrid Search**: Combined vector (pgvector) + full-text (tsvector) search
- **Artifact Generation**: Email drafts, checklists, IRS notice responses, QC memos
- **TaxDome Integration**: Sync documents from TaxDome Drive (Windows)

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [pnpm](https://pnpm.io/) (Node.js package manager)

### Setup

```bash
# 1. Clone and install dependencies
git clone <repo-url>
cd lecpa-agent
uv sync

# 2. Set up environment variables
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and other settings

# 3. Start infrastructure (Postgres, Redis, MinIO)
docker compose -f infra/docker-compose.yml up -d

# 4. Run database migrations
cd apps/api && alembic upgrade head && cd ../..

# 5. Start the services (in separate terminals)
cd apps/api && uvicorn main:app --reload --port 8000
cd services/worker && celery -A main worker --loglevel=info
cd apps/web && pnpm install && pnpm dev
```

### NAS Deployment (Synology Container Station)

For deploying on Synology NAS with direct filesystem access:

```bash
# 1. Prepare NAS directories
ssh admin@192.168.0.6
mkdir -p /volume1/docker/lecpa-agent/{postgres-data,redis-data,logs,config}

# 2. Copy project files
rsync -av --exclude node_modules --exclude .venv \
  . admin@192.168.0.6:/volume1/docker/lecpa-agent/source/

# 3. Update .env for NAS deployment
STORAGE_BACKEND=filesystem
NAS_MOUNT_PATH=/client-files
DEPLOYMENT_TYPE=nas

# 4. Build and start containers
cd /volume1/docker/lecpa-agent/source
docker-compose -f docker-compose.nas.yml up -d --build

# 5. Run migrations
docker exec lecpa-api alembic upgrade head
```

### Verify Setup

```bash
# Check API health
curl http://localhost:8000/health

# Upload a test document
curl -X POST "http://localhost:8000/documents/upload?case_id=<uuid>" \
  -F "file=@path/to/document.pdf"

# Watch worker process the document
# Document status: pending → extracting → chunking → embedding → ready
```

## Architecture

```
apps/
  api/                    # FastAPI backend (orchestrator, auth, case management)
  web/                    # Next.js frontend (chat UI, case workspace)
services/
  worker/                 # Celery workers (ingestion, OCR, embeddings)
  taxdome-sync-agent/     # Windows service for TaxDome Drive sync
  mcp-kb-server/          # MCP server for document search
  mcp-case-server/        # MCP server for case management
packages/
  shared/                 # Shared Pydantic schemas
config/                   # YAML configuration files
```

### Data Flow

1. **Document Upload**: File uploaded via API → stored in configured backend (S3/MinIO or filesystem/NAS)
2. **Ingestion Pipeline**: Celery worker extracts text → OCR if needed → chunks → embeds
3. **Search**: Hybrid vector + full-text search returns relevant chunks with citations
4. **Chat**: Orchestrator retrieves context → LLM generates response with citations

## Configuration

| File | Purpose |
|------|---------|
| `config/model_router.yaml` | LLM provider/model settings (default: Claude Opus 4.5) |
| `config/embeddings.yaml` | Embedding model (default: BGE-small, 384 dims) |
| `config/ocr.yaml` | OCR fallback thresholds |
| `config/folder_rules.yaml` | TaxDome folder parsing rules |

## Environment Variables

```bash
ANTHROPIC_API_KEY=       # Required for Claude models
DATABASE_URL=            # Postgres connection (default: see docker-compose)
REDIS_URL=               # Redis connection (default: redis://localhost:6379/0)
S3_ENDPOINT=             # MinIO/S3 endpoint (default: http://localhost:9000)
S3_ACCESS_KEY=           # MinIO access key (default: minioadmin)
S3_SECRET_KEY=           # MinIO secret key (default: minioadmin)
S3_BUCKET=               # Bucket name (default: lecpa-documents)
STORAGE_BACKEND=         # Storage backend: filesystem or s3 (default: filesystem)
NAS_MOUNT_PATH=          # NAS mount path for filesystem backend (e.g., /client-files)
DEPLOYMENT_TYPE=         # Deployment type: nas, cloud, or local
```

## Development

```bash
# Run tests
pytest                           # All tests
pytest tests/unit/ -v            # Unit tests only
pytest -k "test_name"            # Specific test

# Code quality
uv tool run ruff check .         # Lint
uv tool run ruff format .        # Format
uv tool run mypy apps/api        # Type check

# Database migrations
cd apps/api
alembic upgrade head             # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
```

## Project Status

| Milestone | Status | Description |
|-----------|--------|-------------|
| M1 (Core) | ✅ Complete | Docker infra, ingestion pipeline, hybrid search, chat with citations |
| M2 (TaxDome) | Planned | Windows sync agent, folder mapping, auto-ingestion |
| M3 (Artifacts) | ✅ Complete | Template renderer, 6 Jinja2 templates, artifact storage, IntakeAgent |
| M4 (Extraction) | Planned | W-2/1099/K-1 field extraction, IRS notice response drafts |

## License

Internal use only - Krystal Le CPA
