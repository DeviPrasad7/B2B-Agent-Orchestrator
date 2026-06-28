#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
if [ "$#" -eq 0 ]; then
    echo "Starting Uvicorn..."
    exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WORKERS:-1}
else
    exec "$@"
fi
