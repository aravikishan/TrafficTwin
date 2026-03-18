#!/usr/bin/env bash
# Start TrafficTwin application
set -e

HOST="${TRAFFICTWIN_HOST:-0.0.0.0}"
PORT="${TRAFFICTWIN_PORT:-8007}"

echo "Starting TrafficTwin on $HOST:$PORT"

# Create instance directory for SQLite
mkdir -p instance

# Run with uvicorn
exec uvicorn app:app --host "$HOST" --port "$PORT" --reload
