#!/bin/sh
set -e

# Ensure the data directory exists (Fly.io persistent volume)
mkdir -p /data

# Create or upgrade database tables
flask init-db

exec gunicorn \
  --bind "0.0.0.0:${PORT:-8080}" \
  --workers 2 \
  --timeout 60 \
  --access-logfile - \
  wsgi:app
