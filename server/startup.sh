#!/bin/bash
# Startup script to ensure all required directories exist
# This script is called before starting the Django application

set -e

echo "Creating required directories..."

# Create directories if they don't exist
mkdir -p /app/server/logs
mkdir -p /app/server/static
mkdir -p /app/server/media
mkdir -p /app/server/socket

# Set permissions
chmod -R 755 /app/server/logs
chmod -R 755 /app/server/static
chmod -R 755 /app/server/media
chmod -R 755 /app/server/socket

echo "Directories created successfully."

# Execute the command passed to the script
exec "$@"
