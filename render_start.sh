#!/usr/bin/env bash
# Exit on error
set -e

echo "Activating Node.js environment..."
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

echo "Node.js version available:"
node -v

echo "Starting Uvicorn Server on port $PORT..."
python -m uvicorn backend.api:app --host 0.0.0.0 --port $PORT
