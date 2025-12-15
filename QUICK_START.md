# 🚀 Quick Start: Build & Deploy SoulSync

## ⚡ 5-Minute Quick Deploy

### Windows

```batch
# From SoulSync root directory
build_and_deploy.bat

# Select option 3: "Build, test, and push to Docker Hub"
# Follow prompts to complete build and deployment
```

### Linux/Mac

```bash
# Make script executable
chmod +x build_and_deploy.sh

# Run the script
./build_and_deploy.sh

# Select option 3: "Build, test, and push to Docker Hub"
# Follow prompts to complete build and deployment
```

## 📦 What Gets Built

The build process:
1. ✅ **Tests** the entire test suite (165 tests)
2. ✅ **Builds** Docker image with all dependencies
3. ✅ **Tests** the image locally to verify it works
4. ✅ **Pushes** to Docker Hub for production deployment

## 🐳 After Build: Deploy Locally

```bash
# Create data directories
mkdir data logs downloads

# Start with docker-compose
docker-compose up -d

# Access web UI
# Open http://localhost:8008 in your browser
```

## 🔐 Your Credentials Are Safe

✨ **New Security Feature**: ClientIDs and secrets are now stored **encrypted in a database**, not in plain text files!

- **Encryption Key**: Automatically created at `config/.encryption_key`
- **Database**: Encrypted credentials stored in `database/config.db`
- **Never committed**: Key is in `.gitignore` and never pushed to git

### Backup Your Credentials

```bash
# Back up encryption key and database
mkdir -p backups
cp config/.encryption_key backups/
cp database/config.db backups/
```

## 🌟 Configuration Flow

1. **First Run** → App creates encryption key
2. **Add API Keys** → Web UI encrypts and stores in database
3. **Subsequent Runs** → App decrypts from database automatically

## 📊 Health Check

```bash
# Check if container is running
docker-compose ps

# View logs
docker-compose logs -f soulsync

# Test web server
curl http://localhost:8008/
```

## ❌ Troubleshooting

### Port 8008 Already in Use

```bash
# Change port in docker-compose.yml
# From:  - "8008:8008"
# To:    - "8009:8008"  (or any free port)

docker-compose up -d
```

### Credentials Not Loading

```bash
# Restart the container
docker-compose restart soulsync

# Check logs for errors
docker-compose logs soulsync | grep -i error
```

### Database Locked

```bash
# Stop and restart
docker-compose down
docker-compose up -d
```

## 📈 Next Steps

1. **Access Web UI** → http://localhost:8008
2. **Configure Services** → Add Spotify/Tidal API keys
3. **Set Up Media Server** → Plex, Jellyfin, or Navidrome
4. **Enable Downloads** → Configure Soulseek integration
5. **Start Sync** → Begin syncing playlists!

## 🔗 Quick Links

- **Docker Hub**: https://hub.docker.com/r/boulderbadgedad/soulsync
- **GitHub**: https://github.com/Nezreka/SoulSync
- **Full Guide**: See `BUILD_AND_DEPLOY.md`
- **Issues**: https://github.com/Nezreka/SoulSync/issues

## 🛠️ Manual Docker Commands

### Build Locally

```bash
docker build -t soulsync:latest .
```

### Run Locally

```bash
docker run -d \
  --name soulsync-webui \
  -p 8008:8008 \
  -v $(pwd)/data:/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/downloads:/app/downloads \
  -e FLASK_ENV=production \
  soulsync:latest
```

### Push to Docker Hub

```bash
# Login first
docker login

# Tag and push
docker tag soulsync:latest boulderbadgedad/soulsync:latest
docker push boulderbadgedad/soulsync:latest
```

---

**Your application is now production-ready with secure credential storage! 🎵**
