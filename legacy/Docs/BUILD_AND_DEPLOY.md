# 🚀 SoulSync Build & Deployment Guide

This guide covers building and deploying the SoulSync application with improved secrets management (ClientIDs and secrets stored in database rather than plain text).

## 📋 Prerequisites

- Docker and Docker Compose installed
- Git installed
- Access to Docker Hub account (for pushing images)
- GitHub repository access (for pulling code)

## 🔧 Build Process

### 1. Local Testing (Development)

Before deploying, test locally:

```bash
# Navigate to project directory
cd SoulSync

# Install dependencies
pip install -r requirements-webui.txt

# Run tests to verify everything works
python -m pytest tests/core/ -q

# Start the web server for testing
python web_server.py
# Access at http://localhost:8008
```

### 2. Build Docker Image

```bash
# Build the image locally
docker build -t soulsync:latest .

# Tag for Docker Hub
docker tag soulsync:latest boulderbadgedad/soulsync:latest

# Push to Docker Hub (requires authentication)
docker login
docker push boulderbadgedad/soulsync:latest
```

Or use the provided build script:

```bash
# Make the script executable (on Linux/Mac)
chmod +x ./build_and_deploy.sh

# Run the build script
./build_and_deploy.sh
```

## 🐳 Docker Deployment

### Option 1: Using docker-compose (Recommended)

```bash
# Create data directories
mkdir -p ./data ./logs ./downloads

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f soulsync

# Stop the application
docker-compose down
```

### Option 2: Direct Docker Run

```bash
docker run -d \
  --name soulsync-webui \
  -p 8008:8008 \
  -p 8888:8888 \
  -p 8889:8889 \
  -v $(pwd)/data:/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/downloads:/app/downloads \
  -e FLASK_ENV=production \
  -e PYTHONPATH=/app \
  -e TZ=America/New_York \
  -e PUID=1000 \
  -e PGID=1000 \
  --restart unless-stopped \
  boulderbadgedad/soulsync:latest
```

## 🔐 Secrets Management (Database-Backed)

Your application now stores sensitive credentials (ClientIDs, secrets) in an encrypted database instead of plain text configuration files.

### How It Works

1. **First Run**: Application creates an encryption key at `config/.encryption_key`
2. **Credentials**: When you add API credentials through the web UI, they are encrypted and stored in `database/config.db`
3. **Plain Text Config**: The `config/config.json` no longer contains sensitive values (only structure)

### Security Best Practices

- ✅ **Never commit `.encryption_key` to git** - it's in `.gitignore`
- ✅ **Backup your database** - `database/config.db` contains all encrypted credentials
- ✅ **Backup encryption key** - `config/.encryption_key` is needed to decrypt stored secrets
- ✅ **Use Docker secrets** (production) - Mount encryption key as a Docker secret instead of file
- ✅ **Enable HTTPS** - Use a reverse proxy (nginx/traefik) for production deployments

### Backup Strategy

```bash
# Backup encryption key and database
mkdir -p backups
cp config/.encryption_key backups/
cp database/config.db backups/

# Archive for safekeeping
tar czf soulsync_backup_$(date +%Y%m%d).tar.gz backups/
```

### Restore from Backup

```bash
# Copy backed up files
cp backups/.encryption_key config/
cp backups/config.db database/

# Restart application
docker-compose restart soulsync
```

## 🌐 Deployment Environments

### Development

```bash
docker-compose -f docker-compose.yml up -d
```

### Production (with reverse proxy)

```bash
# Using nginx reverse proxy on port 80/443
# See docker-compose.prod.yml for production setup
docker-compose -f docker-compose.prod.yml up -d
```

### Unraid

```bash
# Follow UNRAID.md for container setup
# Application works as Community App on Unraid
```

## 📊 Health Checks

### Web UI Health Check

```bash
curl http://localhost:8008/health
# Expected: 200 OK with health status
```

### Docker Compose Health Status

```bash
docker-compose ps
# Shows health status: healthy/unhealthy/starting
```

### Container Logs

```bash
# Follow logs in real-time
docker-compose logs -f soulsync

# View last 100 lines
docker-compose logs --tail=100 soulsync

# Search logs for errors
docker-compose logs soulsync | grep ERROR
```

## 🔄 Updating to Latest Version

```bash
# Pull latest code
git pull origin main

# Rebuild image
docker build -t boulderbadgedad/soulsync:latest .

# Recreate containers with new image
docker-compose up -d --build

# Verify health
docker-compose ps
```

## 🐛 Troubleshooting

### Database Locked Error
```bash
# Check container is running
docker-compose ps

# Restart the container
docker-compose restart soulsync
```

### Credentials Not Loading
```bash
# Verify encryption key exists
docker-compose exec soulsync ls -la config/.encryption_key

# Check database permissions
docker-compose exec soulsync ls -la database/config.db

# Restart with fresh initialization
docker-compose down
docker-compose up -d
```

### Port Already in Use
```bash
# Find process using port 8008
lsof -i :8008  # On Linux/Mac
netstat -ano | findstr :8008  # On Windows

# Change port in docker-compose.yml
# ports:
#   - "8008:8008"  # Change first 8008 to desired port
```

## 📈 Performance Tuning

### Resource Limits (docker-compose.yml)

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'        # Max CPU cores
      memory: 2G         # Max memory
    reservations:
      cpus: '0.5'        # Guaranteed CPU
      memory: 512M       # Guaranteed memory
```

### Database Optimization

```bash
# Optimize SQLite database
docker-compose exec soulsync sqlite3 database/config.db "VACUUM;"

# Check database size
docker-compose exec soulsync du -h database/config.db
```

## 📝 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | Flask environment mode |
| `PYTHONPATH` | `/app` | Python module search path |
| `SOULSYNC_DATA_DIR` | `/data` | Data directory path |
| `TZ` | `America/New_York` | Timezone |
| `PUID` | `1000` | Process user ID |
| `PGID` | `1000` | Process group ID |

## 🚀 CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [main]
    tags: [v*]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: boulderbadgedad/soulsync:latest
```

## 📋 Deployment Checklist

- [ ] All tests passing: `pytest tests/core/ -q`
- [ ] Docker image builds successfully: `docker build -t soulsync:latest .`
- [ ] Environment variables configured in docker-compose.yml
- [ ] Data directories created with proper permissions
- [ ] Encryption key backed up securely
- [ ] Database backed up before deployment
- [ ] Health checks passing: `curl http://localhost:8008/health`
- [ ] Web UI accessible at configured port
- [ ] Logs show no critical errors
- [ ] API credentials stored in database (not plain text)
- [ ] HTTPS configured for production (reverse proxy)
- [ ] Auto-restart policy enabled

## 📞 Support

- Repository: https://github.com/Nezreka/SoulSync
- Issues: https://github.com/Nezreka/SoulSync/issues
- Discussions: https://github.com/Nezreka/SoulSync/discussions

---

**Last Updated**: December 15, 2025
**Version**: 1.0 (with Database Secrets)
