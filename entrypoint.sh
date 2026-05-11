#!/bin/bash

# Default to PUID 99 and PGID 100 if not set (Unraid defaults)
USER_ID=${PUID:-99}
GROUP_ID=${PGID:-100}
UMASK_VAL=${UMASK:-022}

echo "--- Initializing SoulSync Container ---"
echo "User ID: $USER_ID"
echo "Group ID: $GROUP_ID"
echo "Umask: $UMASK_VAL"

# Adjust umask
umask $UMASK_VAL

# Update echosync user and group IDs
groupmod -o -g "$GROUP_ID" echosync
usermod -o -u "$USER_ID" echosync

# Ensure volume permissions are correct
echo "Updating permissions on /config and /data..."
chown -R echosync:echosync /config /data /app

# Handle initial config if missing
if [ ! -f "/config/config.json" ]; then
    echo "Initial configuration not found. Copying template..."
    cp /defaults/config.json /config/config.json
    chown echosync:echosync /config/config.json
fi

echo "--- Starting SoulSync with command: $@ ---"
exec gosu echosync "$@"
