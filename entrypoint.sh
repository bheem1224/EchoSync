#!/bin/bash
# SoulSync Docker Entrypoint Script
# Handles PUID/PGID/UMASK configuration for proper file permissions

set -e

# Default values
PUID=${PUID:-1000}
PGID=${PGID:-1000}
UMASK=${UMASK:-022}

echo "🐳 SoulSync Container Starting..."
echo "📝 User Configuration:"
echo "   PUID: $PUID"
echo "   PGID: $PGID"
echo "   UMASK: $UMASK"

# Get current soulsync user/group IDs
CURRENT_UID=$(id -u soulsync)
CURRENT_GID=$(id -g soulsync)

# Only modify user/group if they differ from requested values
if [ "$CURRENT_UID" != "$PUID" ] || [ "$CURRENT_GID" != "$PGID" ]; then
    echo "🔧 Adjusting user permissions..."

    # Modify group ID if needed
    if [ "$CURRENT_GID" != "$PGID" ]; then
        echo "   Changing group ID from $CURRENT_GID to $PGID"
        groupmod -o -g "$PGID" soulsync
    fi

    # Modify user ID if needed
    if [ "$CURRENT_UID" != "$PUID" ]; then
        echo "   Changing user ID from $CURRENT_UID to $PUID"
        usermod -o -u "$PUID" soulsync
    fi

    # Fix ownership of app directories
    echo "🔒 Fixing permissions on app directories..."
    chown -R soulsync:soulsync /config /data 2>/dev/null || true
else
    echo "✅ User/Group IDs already correct"
fi

# Set umask for file creation permissions
echo "🎭 Setting UMASK to $UMASK"
umask "$UMASK"

# Initialize config files if they don't exist (first-time setup)
echo "🔍 Checking for configuration files..."

if [ ! -f "/config/settings.py" ]; then
    echo "   📄 Creating default settings.py..."
    cp /defaults/settings.py /config/settings.py
    chown soulsync:soulsync /config/settings.py
else
    echo "   ✅ settings.py already exists"
fi

# Check encryption key
if [ ! -f "/config/.encryption_key" ]; then
    echo "   ⚠️  WARNING: No encryption key found at /config/.encryption_key"
    echo "   ⚠️  Make sure you have a volume mount: -v ./config:/config"
    echo "   🔐 Key will be generated on first run and should persist to ./config/encryption_key"
else
    echo "   ✅ Encryption key found"
fi

# Ensure all directories exist and have proper permissions
mkdir -p /config /data/logs /data/downloads /data/Transfer
chown -R soulsync:soulsync /config /data

# Final check - verify config is actually mounted
if [ ! -w "/config" ]; then
    echo "❌ ERROR: /config directory is not writable!"
    echo "❌ Check that you have the volume mount: -v ./config:/config"
    echo "❌ And that ./config directory exists on the host"
    exit 1
fi

echo "✅ Configuration directories initialized successfully"
echo "✅ Config directory is writable: $(ls -ld /config)"

# Display final user info
echo "👤 Running as:"
echo "   User: $(id -u soulsync):$(id -g soulsync) ($(id -un soulsync):$(id -gn soulsync))"
echo "   UMASK: $(umask)"
echo ""
echo "🚀 Starting SoulSync Web Server..."

# Execute the main command as the soulsync user
exec gosu soulsync "$@"
