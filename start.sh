#!/bin/bash
# Copy .env.example to .env and fill in your ANTHROPIC_API_KEY, then run this script.
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env — please set your ANTHROPIC_API_KEY in .env before running."
  exit 1
fi

uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
