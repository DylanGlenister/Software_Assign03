#!/bin/bash

APP_MODULE="app.main:app"
HOST="127.0.0.1"
PORT="8000"

if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "No virtual environment found (venv or .venv)."
    exit 1
fi

echo "Starting Uvicorn..."
uvicorn "$APP_MODULE" --host "$HOST" --port "$PORT" --reload

echo
read -p "Uvicorn stopped. Press Enter to close this terminal..."
