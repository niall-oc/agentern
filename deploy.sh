#!/bin/bash

echo "1. Configuring Ollama host binding..."
sudo mkdir -p /etc/systemd/system/ollama.service.d
echo -e "[Service]\nEnvironment=\"OLLAMA_HOST=0.0.0.0\"" | sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null

echo "2. Restarting Ollama service..."
sudo systemctl daemon-reload
sudo systemctl restart ollama

echo "3. Starting Agentern API container..."
if [ -f "docker-compose.yml" ]; then
  docker compose up --build -d
else
  echo "Error: docker-compose.yml not found. You must run this script from inside the agentern directory."
  exit 1
fi

echo "4. Resetting Open WebUI..."
docker rm -f open-webui 2>/dev/null || true

echo "5. Deploying Open WebUI with pre-configured backend connections..."
docker run -d -p 17110:8080 \
  --add-host=host.docker.internal:host-gateway \
  -e OLLAMA_BASE_URL=http://172.17.0.1:11434 \
  -e OPENAI_API_BASE_URL=http://172.17.0.1:17111/v1 \
  -e OPENAI_API_KEY=agentern \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main

echo "Deployment complete. Access the interface at http://localhost:17110"