# Echosync Dockerfile
# Multi-stage build for Svelte Web UI, Rust PyO3 Core, and Python Backend

# ---- Node Stage: Build Svelte Web UI ----
FROM node:20-slim AS node

# 1. Install dependencies in /deps without touching /build
WORKDIR /deps
COPY webui/package.json webui/package-lock.json* ./
RUN npm ci

# 2. Copy source to clean /build directory (zero file collision / overwrite)
WORKDIR /build
COPY webui/ ./
RUN ln -s /deps/node_modules /build/node_modules && npm run build

# ---- Builder Stage: Rust & UV Sync ----
# Use official rust image as the toolchain source to avoid apt-get/rustup churn
FROM rust:slim-bookworm AS rust-toolchain

FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Copy Rust toolchain directly from the official image (zero apt/curl compile churn)
COPY --from=rust-toolchain /usr/local/cargo /usr/local/cargo
COPY --from=rust-toolchain /usr/local/rustup /usr/local/rustup
ENV PATH="/usr/local/cargo/bin:${PATH}"
ENV RUSTUP_HOME="/usr/local/rustup"
ENV CARGO_HOME="/usr/local/cargo"

# Install only the C compiler needed for linking (Debian bookworm avoids Trixie package churn)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv directly from the official astral-sh image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy backend dependency files and Rust source
COPY pyproject.toml uv.lock .python-version Cargo.toml README.md ./
COPY src/ ./src/

ENV UV_PYTHON_DOWNLOADS="never"
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"

# Compile echosync_core and dependencies
RUN uv sync --frozen --no-dev

# ---- Python Stage: Final Application Image ----
FROM python:3.12-slim

WORKDIR /app

# Install runtime system dependencies (no rustc/cargo)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    ffmpeg \
    libchromaprint-tools \
    passwd \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash --uid 1000 echosync

# Copy compiled .venv from builder stage
COPY --from=builder /opt/venv /opt/venv
RUN chmod -R 755 /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create necessary directories
RUN mkdir -p /config /data/logs /data/downloads /data/Transfer /defaults

# Copy application code
COPY . .

# Copy built Svelte UI from the node stage
COPY --from=node /build/build /app/webui/build

# Setup entrypoint
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

# Create template files
RUN cp /app/config/config.example.json /defaults/config.json || true && \
    chmod 644 /defaults/config.json || true

VOLUME ["/config", "/data"]
EXPOSE 5000 5001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/v1/system/health || exit 1

ENV PYTHONPATH=/app
ENV PUID=99
ENV PGID=100
ENV UMASK=022
ENV ECHOSYNC_CONFIG_DIR=/config
ENV ECHOSYNC_DATA_DIR=/data
ENV UVICORN_PORT=5000
ENV TZ=UTC
ENV ECHOSYNC_LOG_LEVEL=INFO

CMD ["/opt/venv/bin/python", "run_api.py"]
