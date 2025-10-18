#!/bin/bash
set -e

# Wait for database to be ready
if [ "$DATABASE_URL" ]; then
    echo "Waiting for database to be ready..."
    python -c "
import time
import sys
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import os

db_url = os.environ.get('DATABASE_URL')
if db_url:
    engine = create_engine(db_url)
    for i in range(30):
        try:
            engine.connect()
            print('Database is ready!')
            break
        except OperationalError:
            print(f'Database not ready, waiting... ({i+1}/30)')
            time.sleep(2)
    else:
        print('Database connection failed after 30 attempts')
        sys.exit(1)
"
fi

# Initialize database if needed
if [ "$1" = "init" ]; then
    echo "Initializing database..."
    python src/cli.py db init
    exit 0
fi

# Run migrations
echo "Running database migrations..."
python src/cli.py db upgrade || true

# Execute the main command
exec "$@"
