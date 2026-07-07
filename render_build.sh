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

echo "Installing Python dependencies (no cache to save RAM)..."
pip install --no-cache-dir -r requirements.txt

echo "Pre-building Master Vite Cache for Zero-Latency AI Scaffolding..."
mkdir -p aion_vite_cache
cd aion_vite_cache
npx -y create-vite@latest client --template react
cd client
# Optimize npm install for limited RAM environments
npm install --legacy-peer-deps --no-audit --no-fund --prefer-offline
npm install react-router-dom axios @mui/material @emotion/react @emotion/styled @mui/icons-material lucide-react recharts tailwindcss --legacy-peer-deps --no-audit --no-fund
echo "Cache built successfully!"
