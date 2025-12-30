# ✅ Pre-Deployment Checklist

Complete this checklist before deploying to production.

## 🧪 Code Quality

- [ ] All 165 tests passing: `pytest tests/core/ -q`
  - [ ] No failing tests
  - [ ] No skipped tests
  - [ ] No warnings

- [ ] Code review completed
  - [ ] Database credentials implementation verified
  - [ ] Encryption key setup confirmed
  - [ ] Config file structure validated

- [ ] No uncommitted changes to critical files
  - [ ] `config/settings.py` - committed
  - [ ] `database/music_database.py` - committed
  - [ ] `web_server.py` - committed

## 🐳 Docker Build

- [ ] Docker and Docker Compose installed
  ```bash
  docker --version
  docker-compose --version
  ```

- [ ] Dockerfile builds successfully
  ```bash
  docker build -t soulsync:latest .
  ```

- [ ] Image size is reasonable (< 1GB)
  ```bash
  docker images | grep soulsync
  ```

- [ ] Container starts without errors
  ```bash
  docker run -d --name test-soulsync soulsync:latest
  docker ps
  docker logs test-soulsync
  docker stop test-soulsync && docker rm test-soulsync
  ```

## 🔐 Secrets Management

- [ ] Encryption key will be created on first run
  - [ ] `.encryption_key` is in `.gitignore`
  - [ ] Never committed to repository

- [ ] Database file exists and is writable
  - [ ] `database/config.db` will be created on first run
  - [ ] Stored in encrypted format

- [ ] Backup plan in place
  - [ ] Know where to backup `.encryption_key`
  - [ ] Know where to backup `config.db`
  - [ ] Have tested backup restoration

- [ ] No plain-text credentials in code
  - [ ] No API keys in `.json` files
  - [ ] No secrets in `.py` files
  - [ ] No tokens in environment variables

## 📋 Configuration

- [ ] `config/config.json` prepared
  - [ ] Has required structure (example can be used)
  - [ ] Sensitive values NOT included (filled via web UI)
  - [ ] Server information correct

- [ ] `docker-compose.yml` configured
  - [ ] Correct port mappings
  - [ ] Volume mounts correct
  - [ ] Environment variables set
  - [ ] Resource limits appropriate

- [ ] Data directories exist and are writable
  ```bash
  mkdir -p data logs downloads
  ls -la data logs downloads
  ```

## 🌐 Networking

- [ ] Ports are available
  - [ ] 8008 (web UI) - available
  - [ ] 8888 (Spotify OAuth) - available
  - [ ] 8889 (Tidal OAuth) - available

- [ ] Firewall allows traffic
  - [ ] Inbound on 8008 from client machines
  - [ ] Outbound to Spotify, Tidal, Plex, etc.

- [ ] Domain/hostname configured (if using reverse proxy)
  - [ ] SSL certificate obtained
  - [ ] Reverse proxy configured

## 📊 Health & Monitoring

- [ ] Health check endpoint responds
  ```bash
  curl http://localhost:8008/health
  ```

- [ ] Logs are created and readable
  - [ ] Log directory writable
  - [ ] Log rotation configured

- [ ] Monitoring/alerting configured
  - [ ] Container health checks enabled
  - [ ] Log monitoring in place
  - [ ] Alert notifications configured

## 📦 Dependencies

- [ ] All Python dependencies installed
  ```bash
  pip install -r requirements-webui.txt
  ```

- [ ] System dependencies available in Docker
  - [ ] Python 3.11+ available
  - [ ] Required system libraries included
  - [ ] Build tools available

## 🔄 Backup & Recovery

- [ ] Backup strategy documented
  - [ ] What to backup (`.encryption_key`, `config.db`)
  - [ ] How often to backup (daily recommended)
  - [ ] Where to store backups (external storage)

- [ ] Recovery procedure tested
  - [ ] Can restore from backup
  - [ ] Credentials recover properly
  - [ ] Data integrity verified

- [ ] Disaster recovery plan
  - [ ] Steps to rebuild from scratch
  - [ ] Timeline for recovery
  - [ ] Contact information documented

## 🚀 Deployment

- [ ] Docker Hub account ready
  - [ ] Logged in to Docker Hub
  - [ ] Repository `boulderbadgedad/soulsync` accessible
  - [ ] Push permissions verified

- [ ] Git repository current
  - [ ] All changes committed
  - [ ] No uncommitted changes
  - [ ] Ready for tag/release

- [ ] Deployment procedure documented
  - [ ] Build steps clear
  - [ ] Push steps clear
  - [ ] Rollback procedure known

- [ ] Team/stakeholders notified
  - [ ] Deployment window scheduled
  - [ ] Downtime expectations set
  - [ ] Contact info available

## ✨ Feature Verification

- [ ] Web UI loads correctly
  - [ ] All pages accessible
  - [ ] Dashboard displays
  - [ ] Settings page loads

- [ ] API credentials work
  - [ ] Spotify auth flow works
  - [ ] Tidal auth flow works (if configured)
  - [ ] Secrets stored encrypted

- [ ] Playlist sync works
  - [ ] Can fetch playlists
  - [ ] Can search for tracks
  - [ ] Can add to wishlist

- [ ] Media server integration works
  - [ ] Plex auth works (if configured)
  - [ ] Jellyfin auth works (if configured)
  - [ ] Navidrome auth works (if configured)

## 📝 Documentation

- [ ] README.md is current
  - [ ] Installation instructions accurate
  - [ ] Configuration steps correct
  - [ ] Troubleshooting section helpful

- [ ] BUILD_AND_DEPLOY.md is complete
  - [ ] Build steps documented
  - [ ] Deployment options clear
  - [ ] Troubleshooting included

- [ ] QUICK_START.md is accessible
  - [ ] 5-minute deploy procedure working
  - [ ] Quick links correct
  - [ ] Troubleshooting accurate

- [ ] Deployment notes prepared
  - [ ] What changed documented
  - [ ] Breaking changes identified
  - [ ] Migration steps (if any) documented

## ✅ Final Checks

- [ ] All above checkboxes completed
- [ ] No critical TODOs remaining
- [ ] Code review approved
- [ ] Change log updated
- [ ] Version bumped (if applicable)
- [ ] Ready for production deployment ✨

---

## 🎬 Deployment Command

```bash
# Windows
build_and_deploy.bat

# Linux/Mac
./build_and_deploy.sh
```

Select option 3: "Build, test, and push to Docker Hub"

---

**Deployment Date**: ________________
**Deployed By**: ________________
**Approval**: ________________
