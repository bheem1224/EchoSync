# Echosync Dockerfile
# Multi-stage build for Svelte Web UI and Python Backend

# ---- Node Stage: Build Svelte Web UI ----
FROM node:20-slim AS node

WORKDIR /app/webui

# Copy package files and install dependencies
COPY webui/package.json webui/package-lock.json* ./
# A standard npm install is safe here since we fixed the dependencies in package.json
RUN npm install

# Copy the rest of the web UI source code
COPY webui ./

# Build the Svelte application
RUN npm run build

# ---- Python Stage: Final Application Image ----
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    ffmpeg \
    libchromaprint-tools \
    passwd \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 echosync

# --- UV INSTALLATION & DEPENDENCY SYNC ---
# Install uv directly from the official astral-sh image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy backend dependency files
COPY pyproject.toml uv.lock .python-version ./

ENV UV_PYTHON_DOWNLOADS="never"

# 1. Force uv to build the environment OUTSIDE of /app
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"

# Use uv to sync the environment exactly as it is in uv.lock
RUN uv sync --frozen --no-dev

# fix unraid permissions error
RUN chmod -R 755 /opt/venv

# Put the uv virtual environment in the PATH so 'python' automatically uses it
ENV PATH="/opt/venv/bin:$PATH"
# ------------------------------------------

# Create necessary directories
RUN mkdir -p /config /data/logs /data/downloads /data/Transfer /defaults

# Copy application code 
COPY . .

# Copy built Svelte UI from the node stage
COPY --from=node /app/webui/build /app/webui/build

# Setup entrypoint
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Create template files
# (Using || true to ensure build doesn't fail if example config is missing)
RUN cp /app/config/config.example.json /defaults/config.json || true && \
    chmod 644 /defaults/config.json || true

# Create volume mount points
VOLUME ["/config", "/data"]

# Expose ports for web app and OAuth callbacks
EXPOSE 5000 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1
# Set environment variables
ENV PYTHONPATH=/app
ENV PUID=99
ENV PGID=100
ENV UMASK=022
ENV ECHOSYNC_CONFIG_DIR=/config
ENV ECHOSYNC_DATA_DIR=/data
ENV UVICORN_PORT=5000
ENV TZ=UTC
ENV ECHOSYNC_LOG_LEVEL=INFO

# Default command; used as arguments to the entrypoint
CMD ["/opt/venv/bin/python", "run_api.py"]