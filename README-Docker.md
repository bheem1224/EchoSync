# SoulSync WebUI - Docker Deployment Guide

## 🐳 Quick Start

### Prerequisites
- Docker Engine 20.10+
- Docker Compose 1.29+
- At least 2GB RAM and 10GB free disk space

### 1. Setup
```bash
# Clone or download the repository
git clone <your-repo-url>
cd newmusic

# Run setup script
chmod +x docker-setup.sh
./docker-setup.sh
```

### 2. Configure
Configuration is now managed directly within the SoulSync web UI and stored securely in an encrypted database file (`database/music_library.db`).

On first launch, SoulSync will start with a default configuration. To get started:
1. Access the web UI at `http://localhost:8008`.
2. Navigate to the **Settings** page.
3. Enter your API keys and other server settings.

If you are migrating from an older version of SoulSync, your existing `config/config.json` will be automatically imported into the new system on the first run. After migration, `config.json` is no longer used.

### 3. Deploy
```bash
# Start SoulSync
docker-compose up -d

# View logs
docker-compose logs -f

# Access the web interface
open http://localhost:8008
```

## 📁 Volume Mounts

SoulSync requires persistent storage for your configuration, database, and logs. It is designed to use a single data directory to make this easy.

- **`./data`** → `/data` - Stores all configuration and the application database.
- **`./logs`** → `/app/logs` - Application logs.

You will also need to mount any directories you want SoulSync to access, such as your music library or download folders. The `docker-compose.yml` provides examples for this.

## 🔧 Configuration Options

### Environment Variables
```yaml
environment:
  - FLASK_ENV=production              # Flask environment
  - PYTHONPATH=/app                   # Python path
  - TZ=America/New_York               # Timezone
  - SOULSYNC_DATA_DIR=/data           # Location for config and database
```

### Port Configuration
Default port is `8008`. To change:
```yaml
ports:
  - "9999:8008"  # Access on port 9999
```

### Resource Limits
Adjust based on your system:
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'      # Max CPU cores
      memory: 4G       # Max RAM
    reservations:
      cpus: '1.0'      # Minimum CPU
      memory: 1G       # Minimum RAM
```

## 🚀 Advanced Setup

### Multi-Architecture Support
The Docker image supports both AMD64 and ARM64:
```bash
# Build for specific architecture
docker buildx build --platform linux/amd64,linux/arm64 -t soulsync-webui .
```

### Custom Network
For integration with other containers:
```yaml
networks:
  media:
    external: true
```

### External Services
Connect to external Plex/Jellyfin servers:
```yaml
extra_hosts:
  - "plex.local:192.168.1.100"
  - "jellyfin.local:192.168.1.101"
```

## 🔍 Troubleshooting

### Check Container Status
```bash
docker-compose ps
docker-compose logs soulsync
```

### Common Issues

**Permission Denied**
```bash
sudo chown -R 1000:1000 config database logs downloads Transfer
```

**Port Already in Use**
```bash
# Check what's using port 8888
sudo lsof -i :8888
# Change port in docker-compose.yml
```

**Out of Memory**
```bash
# Increase memory limits in docker-compose.yml
# Or free up system memory
```

### Health Check
The container includes health checks:
```bash
docker inspect --format='{{.State.Health.Status}}' soulsync-webui
```

## 📊 Monitoring

### View Real-time Logs
```bash
docker-compose logs -f --tail=100
```

### Container Stats  
```bash
docker stats soulsync-webui
```

### Database Size
```bash
du -sh database/
```

## 🔄 Updates

### Pull Latest Image
```bash
docker-compose pull
docker-compose up -d
```

### Backup Before Update
```bash
# Backup data
tar -czf soulsync-backup-$(date +%Y%m%d).tar.gz config/ database/ logs/

# Update
docker-compose pull && docker-compose up -d
```

## 🛠️ Development

### Build Local Image
```bash
docker build -t soulsync-webui .
```

### Development Mode
```yaml
# In docker-compose.yml
environment:
  - FLASK_ENV=development
volumes:
  - .:/app  # Mount source code for live reload
```

## 🔐 Security

### Non-Root User
The container runs as user `soulsync` (UID 1000) for security.

### Network Security
```yaml
# Restrict to localhost only
ports:
  - "127.0.0.1:8888:8888"
```

### Firewall
```bash
# Allow only local access
sudo ufw allow from 192.168.1.0/24 to any port 8888
```

## 📋 Complete Example

Here's a complete `docker-compose.yml` for production:

```yaml
version: '3.8'

services:
  soulsync:
    image: boulderbadgedad/soulsync:latest # or build: . if you build your own image
    container_name: soulsync-webui
    restart: unless-stopped
    ports:
      - "8008:8008"      # Main web app
      - "8888:8888"      # Spotify OAuth callback
      - "8889:8889"      # Tidal OAuth callback
    volumes:
      - ./data:/data
      - ./logs:/app/logs
      - /path/to/your/music:/music:ro
      - /path/to/your/downloads:/downloads
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
      - SOULSYNC_DATA_DIR=/data
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8888/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 🎯 Production Checklist

- [ ] Configure proper API keys in the Web UI settings page
- [ ] Set appropriate resource limits
- [ ] Configure proper volume mounts
- [ ] Set up log rotation
- [ ] Configure firewall rules
- [ ] Set up backup strategy
- [ ] Test health checks
- [ ] Verify external service connectivity