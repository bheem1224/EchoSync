# Echosync Dockerfile
# Multi-stage build for Svelte Web UI, Rust PyO3 Core, and Python Backend

# ---- Pre-compiled Binary Sources ----
FROM mwader/static-ffmpeg:latest AS ffmpeg-source
FROM tianon/gosu:latest AS gosu-source

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
FROM rust:slim-bookworm AS rust-toolchain

# Full bookworm image includes gcc, libc6-dev, and build utilities pre-baked
FROM python:3.12-bookworm AS builder

WORKDIR /app

# Copy Rust toolchain directly from official image
COPY --from=rust-toolchain /usr/local/cargo /usr/local/cargo
COPY --from=rust-toolchain /usr/local/rustup /usr/local/rustup
ENV PATH="/usr/local/cargo/bin:${PATH}"
ENV RUSTUP_HOME="/usr/local/rustup"
ENV CARGO_HOME="/usr/local/cargo"

# Install uv directly from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency specifications and Rust source
COPY pyproject.toml uv.lock .python-version Cargo.toml README.md ./
COPY src/ ./src/

ENV UV_PYTHON_DOWNLOADS="never"
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"

# Compile echosync_core and synchronize dependencies (zero apt-get / dpkg calls)
RUN uv sync --frozen --no-dev

# ---- Python Stage: Final Application Image ----
FROM python:3.12-bookworm

WORKDIR /app

# Copy pre-compiled static runtime binaries (Zero apt-get / dpkg calls)
COPY --from=ffmpeg-source /ffmpeg /ffprobe /usr/local/bin/
COPY --from=gosu-source /gosu /usr/local/bin/
RUN chmod 755 /usr/local/bin/ffmpeg /usr/local/bin/ffprobe /usr/local/bin/gosu

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1000 echosync

# Copy compiled venv from builder stage
COPY --from=builder /opt/venv /opt/venv
RUN chmod -R 755 /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create directories and copy source
RUN mkdir -p /config /data/logs /data/downloads /data/Transfer /defaults
COPY . .
COPY --from=node /build/build /app/webui/build

RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]

RUN cp /app/config/config.example.json /defaults/config.json || true && \
    chmod 644 /defaults/config.json || true

VOLUME ["/config", "/data"]
EXPOSE 5000 5001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/api/v1/system/health')" || exit 1

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
