#!/bin/bash

# Run migrations (if any)
# alembic upgrade head

if [ "$DEBUG" = "true" ]; then
    echo "Starting in DEVELOPMENT mode..."
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    echo "Starting in PRODUCTION mode..."
    # 4 workers is a good starting point for a small server
    exec gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
fi
