#!/bin/bash
set -e

# Set file descriptor limits to prevent "Too many open files" errors
ulimit -n 65536

# Copy secret if present (Render)
if [ -f /etc/secrets/gcp_key.json ]; then
  echo "Render secret found. Copying to /tmp..."
  cp /etc/secrets/gcp_key.json /tmp/gcp_key.json
  chmod 600 /tmp/gcp_key.json
  chown app:app /tmp/gcp_key.json
  export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_key.json
fi

# Drop to non-root user
exec su -s /bin/bash app -c "$*"

# Execute the main command
echo "Starting application..."
exec "$@" 