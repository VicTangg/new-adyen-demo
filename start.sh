#!/usr/bin/env bash
# Activate virtual environment and start the Flask app.
# The app loads .env from the project root automatically via run.py.

set -e
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  echo "Virtual environment not found. Run: python -m venv .venv && pip install -r requirements.txt"
  exit 1
fi

# Activate venv and run the app (run.py loads .env via dotenv)
source .venv/bin/activate
exec python run.py
