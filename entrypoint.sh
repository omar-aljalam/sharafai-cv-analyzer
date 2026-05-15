#!/bin/sh

export PATH="/app/.venv/bin:$PATH"

echo "Waiting for the database to be ready..."
while ! nc -z postgres_db 5432; do
    sleep 0.5
done
echo "PostgreSQL is up and running!"

echo "Executing database migrations..."
alembic upgrade head

echo "Starting the FastAPI application..."
# For Development, you might want to use `fastapi dev` for auto-reloading.
exec fastapi dev app/main.py --host 0.0.0.0 --port "$PORT" --proxy-headers --forwarded-allow-ips '*'
# For Production, use `fastapi run` for better performance.
# exec fastapi run app/main.py --host 0.0.0.0 --port "$PORT" --proxy-headers --forwarded-allow-ips '*'
