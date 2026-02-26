# SoulSync Dockerfile (UV Optimized)
# Multi-stage build for Svelte Web UI and Python Backend

# ---- Stage 1: Build Svelte Web UI ----
FROM node:20-slim as frontend-builder

WORKDIR /app/webui

# Copy package files and install dependencies
COPY webui/package.json webui/package-lock.json* ./
RUN npm install

# Copy the rest of the web UI source code
COPY webui ./

# Build the Svelte application (outputs to build/ or dist/)
RUN npm run build

# ---- Stage 2: Python Backend (UV) ----
# Using python:3.12-slim as base since 3.14 is not standard yet in most registries.
# If 3.14 is explicitly required by pyproject.toml, ensure a compatible image exists.
# For stability, we use 3.12-slim-bookworm which is modern and stable.
FROM python:3.12-slim-bookworm

# Copy uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PUID=1000 \
    PGID=1000 \
    SOULSYNC_CONFIG_DIR=/config \
    SOULSYNC_DATA_DIR=/data \
    PATH="/app/.venv/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 soulsync && \
    useradd -u 1000 -g soulsync -s /bin/bash -m soulsync

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install dependencies using uv
# --frozen: require uv.lock to be up-to-date
# --no-dev: do not install dev dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Copy built frontend assets from Stage 1
# Assuming SvelteKit adapter-static outputs to 'build' by default
# We place it in webui/build so Flask can serve it if configured, or Nginx
COPY --from=frontend-builder /app/webui/build /app/webui/build

# Create config and data directories
RUN mkdir -p /config /data/logs /data/downloads /data/library /data/plugins && \
    chown -R soulsync:soulsync /config /data /app

# Expose ports
# 5000: API/WebUI
# 8888, 8889: OAuth callbacks
EXPOSE 5000 8888 8889

# Volumes
VOLUME ["/config", "/data"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/api/v1/health || exit 1

# Entrypoint script to handle PUID/PGID and permissions
COPY --chmod=755 <<EOF /entrypoint.sh
#!/bin/bash
set -e

# Fix permissions if running as root (Docker default)
if [ "$(id -u)" = '0' ]; then
    groupmod -o -g "\$PGID" soulsync
    usermod -o -u "\$PUID" soulsync

    chown -R soulsync:soulsync /config /data

    exec gosu soulsync "\$@"
else
    exec "\$@"
fi
EOF

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "run_api.py"]
