#!/bin/sh
set -e

alembic upgrade head

if [ "${RUN_SEED:-false}" = "true" ]; then
    echo "[entrypoint] seeding base content"
    python -m scripts.seed
fi

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --proxy-headers \
    --forwarded-allow-ips="${FORWARDED_ALLOW_IPS:-*}"
