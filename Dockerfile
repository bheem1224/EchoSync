# SoulSync WebUI Dockerfile
# Multi-architecture support for AMD64 and ARM64

# ---- Builder Stage ----
# This stage installs dependencies, including build-time tools, to keep the final image lean.
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build-time system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python -m venv /opt/venv

# Activate virtual environment for subsequent commands
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements-webui.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-webui.txt

# ---- Final Stage ----
# This stage creates the final, lean production image.
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

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Activate the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY . .

# Create necessary directories with proper permissions
RUN mkdir -p /config /data/logs /data/downloads /data/Transfer && \
    chown -R soulsync:soulsync /config /data

# Create defaults directory and copy template files
# These will be used by entrypoint.sh to initialize empty volumes
RUN mkdir -p /defaults && \
    cp /app/config/config.example.json /defaults/config.json && \
    cp /app/config/settings.py /defaults/settings.py && \
    chmod 644 /defaults/config.json /defaults/settings.py

# Create volume mount points
VOLUME ["/config", "/data"]

# Copy and set up entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Note: Don't switch to soulsync user yet - entrypoint needs root to change UIDs
# The entrypoint script will switch to soulsync after setting up permissions

# Expose ports for web app and OAuth callbacks
EXPOSE 8008 8888 8889

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8008/ || exit 1

# Set environment variables
ENV PYTHONPATH=/app
ENV FLASK_APP=web_server.py
ENV FLASK_ENV=production
ENV PUID=1000
ENV PGID=1000
ENV UMASK=022
ENV SOULSYNC_CONFIG_DIR=/config
ENV SOULSYNC_DATA_DIR=/data
# default timezone and log verbosity (can be overridden at runtime)
ENV TZ=UTC
ENV SOULSYNC_LOG_LEVEL=INFO

# Set entrypoint and default command
ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "web_server.py"]