# SoulSync Dockerfile
# Multi-stage build for Svelte Web UI and Python Backend

# ---- Node Stage: Build Svelte Web UI ----
FROM node:20-slim as node

WORKDIR /app/webui

# Copy package files and install dependencies
COPY webui/package.json webui/package-lock.json* ./
# install using legacy peer deps to bypass transient conflicts between
# vite and the Svelte plugin; the lockfile (if present) will pin versions
RUN npm install --legacy-peer-deps

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

# Install Python dependencies using pyproject.toml (PEP 517 project)
# copying only the metadata files first allows Docker layer caching
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy application code (legacy files have been removed from repository)
COPY . .

# Copy built Svelte UI from the node stage
COPY --from=node /app/webui/build /app/webui/build

# Create necessary directories with proper permissions
RUN mkdir -p /config /data/logs /data/downloads /data/Transfer && \
    chown -R soulsync:soulsync /config /data

# Create defaults directory and copy template files
# These will be used by entrypoint.sh to initialize empty volumes
RUN mkdir -p /defaults && \
    cp /app/config/config.example.json /defaults/config.json && \
    chmod 644 /defaults/config.json

# Create volume mount points
VOLUME ["/config", "/data"]

# The previous entrypoint script was removed during refactor; backend
# now starts directly via the default command below.

# Expose ports for web app and OAuth callbacks
EXPOSE 5000 8888 8889

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

# Default command; no entrypoint script is used any more
CMD ["python", "run_api.py"]
