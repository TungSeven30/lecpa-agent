# =============================================================================
# Krystal Le Agent - Celery Worker Container
# =============================================================================
# Multi-stage build for Celery worker with document processing capabilities
# Includes OCR, PDF parsing, and embedding generation
# =============================================================================

FROM python:3.11-slim as base

# Environment variables for Python optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for document processing
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------------------------------------
# Builder stage - Install Python dependencies
# -----------------------------------------------------------------------------
FROM base as builder

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./
COPY packages/ ./packages/
COPY services/worker/pyproject.toml ./services/worker/

# Install dependencies using uv
RUN uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Runtime stage - Final image
# -----------------------------------------------------------------------------
FROM base as runtime

# Create non-root user for security
RUN useradd -m -u 1000 lecpa && \
    mkdir -p /app /client-files /app/logs && \
    chown -R lecpa:lecpa /app /app/logs

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder --chown=lecpa:lecpa /app/.venv /app/.venv

# Copy application code
COPY --chown=lecpa:lecpa services/worker/ ./services/worker/
COPY --chown=lecpa:lecpa packages/ ./packages/
COPY --chown=lecpa:lecpa config/ ./config/

# Add .venv to PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/packages:/app/services/worker:$PYTHONPATH"

# Switch to non-root user
USER lecpa

# Run Celery worker
# - Concurrency=2: Process 2 tasks in parallel (adjust based on NAS CPU)
# - Max tasks per child=100: Restart workers to prevent memory leaks
# - Loglevel=info: Balanced logging
CMD ["celery", "-A", "services.worker.main", "worker", \
     "--loglevel=info", \
     "--concurrency=2", \
     "--max-tasks-per-child=100", \
     "--task-events"]
