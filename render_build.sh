#!/usr/bin/env bash
# Exit on error
set -e

echo "Installing Node.js via NVM..."
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

nvm install 20
nvm use 20

echo "Node.js installed successfully:"
node -v
npm -v

echo "Installing Python dependencies..."
pip install -r backend/requirements.txt
