# SoulSync Dockerfile
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
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 soulsync

# --- UV INSTALLATION & DEPENDENCY SYNC ---
# Install uv directly from the official astral-sh image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy backend dependency files
COPY pyproject.toml uv.lock .python-version ./

# Use uv to sync the environment exactly as it is in uv.lock
RUN uv sync --frozen --no-dev

# Put the uv virtual environment in the PATH so 'python' automatically uses it
ENV PATH="/app/.venv/bin:$PATH"
# ------------------------------------------

# Copy application code 
COPY . .

# Copy built Svelte UI from the node stage
COPY --from=node /app/webui/build /app/webui/build

# Create necessary directories with proper permissions
RUN mkdir -p /config /data/logs /data/downloads /data/Transfer && \
    chown -R soulsync:soulsync /config /data

# Create defaults directory and copy template files
# (Using || true to ensure build doesn't fail if example config is missing)
RUN mkdir -p /defaults && \
    cp /app/config/config.example.json /defaults/config.json || true && \
    chmod 644 /defaults/config.json || true

# Create volume mount points
VOLUME ["/config", "/data"]

# Expose ports for web app and OAuth callbacks
EXPOSE 5000 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/v1/health || exit 1

# Set environment variables
ENV PYTHONPATH=/app
ENV PUID=1000
ENV PGID=1000
ENV UMASK=022
ENV SOULSYNC_CONFIG_DIR=/config
ENV SOULSYNC_DATA_DIR=/data
ENV UVICORN_PORT=5000
# default timezone and log verbosity (can be overridden at runtime)
ENV TZ=UTC
ENV SOULSYNC_LOG_LEVEL=INFO

# Default command; using the uv virtual environment
CMD ["python", "run_api.py"]