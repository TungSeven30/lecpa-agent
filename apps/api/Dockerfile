# =============================================================================
# Krystal Le Agent - API Container
# =============================================================================
# Multi-stage build for FastAPI backend with Python 3.11
# Optimized for production deployment on Synology NAS
# =============================================================================

FROM python:3.11-slim as base

# Environment variables for Python optimization
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
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
COPY apps/api/pyproject.toml ./apps/api/

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
COPY --chown=lecpa:lecpa apps/api/ ./apps/api/
COPY --chown=lecpa:lecpa packages/ ./packages/
COPY --chown=lecpa:lecpa config/ ./config/

# Add .venv to PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/packages:/app/apps/api:$PYTHONPATH"

# Switch to non-root user
USER lecpa

# Expose port
EXPOSE 8008

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8008/health || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8008", "--workers", "2"]
