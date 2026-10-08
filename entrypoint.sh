#!/bin/sh
set -e

echo "Attendo PostgreSQL..."

python - <<'PY'
import os
import socket
import time

host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))

for attempt in range(60):
    try:
        with socket.create_connection((host, port), timeout=2):
            print("PostgreSQL raggiungibile.")
            break
    except OSError:
        print(f"PostgreSQL non ancora disponibile ({attempt + 1}/60)...")
        time.sleep(2)
else:
    raise SystemExit("PostgreSQL non raggiungibile.")
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
