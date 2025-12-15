# 📦 How to Deploy Right Now

## ⚡ TL;DR - Deploy in 2 Minutes

### Windows
```batch
build_and_deploy.bat
# Choose option 3, follow prompts
```

### Linux/Mac
```bash
chmod +x build_and_deploy.sh
./build_and_deploy.sh
# Choose option 3, follow prompts
```

That's it! The script handles everything:
- ✅ Tests (165 tests)
- ✅ Builds Docker image
- ✅ Tests image locally
- ✅ Pushes to Docker Hub
- ✅ Shows next steps

---

## 🎯 Deployment Options

### Option 1: Full Build + Test + Push (Recommended)
```bash
# Windows
build_and_deploy.bat
# Choose: 3

# Linux/Mac
./build_and_deploy.sh
# Choose: 3
```

**What it does**:
1. Verifies Docker is installed
2. Runs full test suite (165 tests)
3. Builds Docker image
4. Tests image in real container
5. Logs into Docker Hub
6. Pushes image to registry
7. Shows deployment instructions

**Time**: ~5-10 minutes

### Option 2: Build Only (No Push)
```bash
# Windows
build_and_deploy.bat
# Choose: 1

# Linux/Mac
./build_and_deploy.sh
# Choose: 1
```

**What it does**:
1. Verifies Docker is installed
2. Builds Docker image locally
3. Shows deployment instructions

**Time**: ~2 minutes
**Good for**: Testing locally before pushing

### Option 3: Build + Test (No Push)
```bash
# Windows
build_and_deploy.bat
# Choose: 2

# Linux/Mac
./build_and_deploy.sh
# Choose: 2
```

**What it does**:
1. Verifies Docker is installed
2. Runs full test suite
3. Builds Docker image
4. Tests image in real container
5. Shows deployment instructions

**Time**: ~5 minutes
**Good for**: Final verification before pushing

### Option 4: Test Existing Image
```bash
# Windows
build_and_deploy.bat
# Choose: 4

# Linux/Mac
./build_and_deploy.sh
# Choose: 4
```

**What it does**:
1. Tests an already-built image
2. Verifies it works correctly

**Time**: ~1-2 minutes
**Good for**: Verifying a previously built image

---

## 🚦 Step-by-Step: Full Deployment

### 1. Open Terminal/Command Prompt

**Windows**:
- Press `Win+X` → "Windows Terminal" or "Command Prompt"
- Or: Search for "cmd" → Open

**Linux/Mac**:
- Terminal application (usually installed by default)

### 2. Navigate to Project

```bash
cd C:\Users\bheam\VScode-Projects\SoulSync  # Windows
# or
cd ~/path/to/SoulSync                       # Linux/Mac
```

### 3. Run Deployment Script

**Windows**:
```batch
build_and_deploy.bat
```

**Linux/Mac**:
```bash
chmod +x build_and_deploy.sh
./build_and_deploy.sh
```

### 4. Choose Option 3

```
Select action:
1) Build Docker image (local testing)
2) Build and test Docker image
3) Build, test, and push to Docker Hub
4) Just test existing image
5) Show deployment instructions
6) Exit

Enter choice [1-6]: 3
```

Type `3` and press Enter

### 5. Enter Docker Hub Password

When prompted:
```
Username: boulderbadgedad
Password: [Enter your Docker Hub password]
```

Your password will be hidden (don't panic!)

### 6. Watch the Process

The script will:
1. ✅ Check Docker installation
2. ✅ Run 165 tests
3. ✅ Build image (2-5 minutes)
4. ✅ Test image (1 minute)
5. ✅ Push to Docker Hub (1-2 minutes)

You'll see progress output like:
```
================================
Building Docker Image
================================
Building image: boulderbadgedad/soulsync:latest
[... build output ...]
Step 1/20 : FROM python:3.11-slim
[... more output ...]
Successfully tagged boulderbadgedad/soulsync:latest
✓ Docker image built successfully
```

### 7. Deployment Complete!

When finished, you'll see:
```
================================
Deployment Instructions
================================

✓ Build and push completed successfully!

To deploy the application:
...
```

---

## 🐳 Deploy to Server After Build

Once the script finishes, deploy on your server:

### Quick Deployment
```bash
# Create data directories
mkdir data logs downloads

# Start the application
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f soulsync
```

### Access Web UI
```
http://localhost:8008
```

If deployed on server:
```
http://your-server-ip:8008
```

---

## ⚡ Quick Verification

### Is the container running?
```bash
docker-compose ps
# Should show: soulsync-webui  Up
```

### Can I access the web UI?
```bash
curl http://localhost:8008/
# Should return HTML page
```

### Are there any errors?
```bash
docker-compose logs soulsync | head -50
# Should show initialization messages, not errors
```

### All good?
✅ You're deployed!

---

## 🔍 If Something Goes Wrong

### Error: "Docker not found"
```bash
# Install Docker
# Windows: https://www.docker.com/products/docker-desktop
# Linux: https://docs.docker.com/engine/install/
# Mac: https://www.docker.com/products/docker-desktop
```

### Error: "Port 8008 already in use"
```bash
# Change port in docker-compose.yml
# From: - "8008:8008"
# To:   - "8009:8008"

docker-compose up -d
```

### Error: "Docker login failed"
```bash
# Make sure you have a Docker Hub account
# https://hub.docker.com/signup

# Try logging in manually
docker login
# Enter username and password

# Then run script again
build_and_deploy.bat  # Windows
./build_and_deploy.sh # Linux/Mac
```

### Error: "Tests failed"
```bash
# Run tests locally to see what's wrong
pytest tests/core/ -q

# If all pass locally, try building again:
build_and_deploy.bat  # Windows
./build_and_deploy.sh # Linux/Mac
```

### Error: "Container won't start"
```bash
# Check logs
docker-compose logs soulsync

# Try restarting
docker-compose down
docker-compose up -d

# Check logs again
docker-compose logs -f soulsync
```

### Get help
See **BUILD_AND_DEPLOY.md** → Troubleshooting section

---

## 📝 What Gets Deployed

```
Your Docker image includes:
├── Python 3.11 runtime
├── All Python dependencies
├── SoulSync application code
│   ├── Web server
│   ├── API integrations (Spotify, Tidal, etc.)
│   ├── Media server support (Plex, Jellyfin, Navidrome)
│   ├── Soulseek integration
│   └── Database management
├── Configuration system (database-backed)
└── Startup scripts
```

**Size**: ~600-800MB

---

## 🔐 Your Secrets Are Safe

✅ **Encrypted Storage**
- Credentials stored in: `database/config.db`
- Encryption key in: `config/.encryption_key`
- Never in plain text

✅ **Automatic Encryption**
- When you add API keys via web UI
- They're encrypted before storage
- Decrypted when needed

✅ **Backup Strategy**
```bash
# Backup these files
cp config/.encryption_key backups/
cp database/config.db backups/
```

---

## 🎉 After Deployment

1. **Access Web UI**: http://localhost:8008
2. **Login/Register**: Create your account
3. **Add API Keys**: Spotify, Tidal, etc.
4. **Configure Media Server**: Plex, Jellyfin, Navidrome
5. **Start Syncing**: Begin syncing playlists!

---

## 🚀 Summary

| Step | Command | Time |
|------|---------|------|
| **1. Open Terminal** | (manual) | - |
| **2. Navigate to folder** | `cd SoulSync` | - |
| **3. Run script** | `build_and_deploy.bat` (or `.sh`) | - |
| **4. Choose option** | `3` | - |
| **5. Enter password** | `your-docker-password` | - |
| **6. Wait** | (automated) | 5-10 min |
| **7. Deploy locally** | `docker-compose up -d` | 1 min |
| **8. Access** | `http://localhost:8008` | - |

**Total time**: ~10-15 minutes (mostly automated)

---

**Ready to deploy? Run the script now!** 🚀

```bash
# Windows
build_and_deploy.bat

# Linux/Mac
chmod +x build_and_deploy.sh
./build_and_deploy.sh
```

Choose option `3` and follow the prompts. That's all! 🎵
