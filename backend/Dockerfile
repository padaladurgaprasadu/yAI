FROM python:3.11-slim

# Install Node.js and npm
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-build the Master Vite Cache so AI scaffolding is instant (Zero-Latency)
RUN mkdir -p aion_vite_cache \
    && cd aion_vite_cache \
    && npx -y create-vite@latest client --template react \
    && cd client \
    && npm install --legacy-peer-deps \
    && npm install react-router-dom axios @material-ui/core @material-ui/icons lucide-react recharts tailwindcss --legacy-peer-deps

# Copy the rest of the backend code
COPY . .

# Expose the API port
EXPOSE 5000

# Start the FastAPI server using the PORT environment variable provided by Render
CMD sh -c "uvicorn api_real:app --host 0.0.0.0 --port ${PORT:-5000}"
