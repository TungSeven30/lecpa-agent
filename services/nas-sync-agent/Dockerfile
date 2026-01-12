# NAS Sync Agent Dockerfile
# Monitors NAS filesystem and syncs documents to Le CPA Agent

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY nas_sync/ nas_sync/

# Install dependencies using uv
RUN uv pip install --system -e .

# Create state directory for SQLite database
RUN mkdir -p /app/state

# Create non-root user for security
RUN useradd -m -u 1000 syncagent
RUN chown -R syncagent:syncagent /app

USER syncagent

# Default command: start the watcher
ENTRYPOINT ["python", "-m", "nas_sync.main"]
CMD ["watch", "--config", "/app/config.yaml"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import nas_sync; print('healthy')" || exit 1

# Labels
LABEL org.opencontainers.image.title="NAS Sync Agent"
LABEL org.opencontainers.image.description="Filesystem sync agent for Le CPA Agent"
LABEL org.opencontainers.image.version="0.1.0"
