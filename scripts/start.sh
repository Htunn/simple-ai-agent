#!/bin/bash
set -e

echo "🚀 Starting Clawbot AI Agent..."

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
while ! pg_isready -h postgres -U clawbot > /dev/null 2>&1; do
  sleep 1
done
echo "✅ PostgreSQL is ready"

# Wait for Redis
echo "⏳ Waiting for Redis..."
while ! redis-cli -h redis ping > /dev/null 2>&1; do
  sleep 1
done
echo "✅ Redis is ready"

# Run database migrations
echo "📊 Running database migrations..."
python scripts/init_db.py

# Start the application
echo "🤖 Starting application..."
exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
