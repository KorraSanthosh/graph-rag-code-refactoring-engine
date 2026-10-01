#!/bin/bash
# EC2 user-data for Amazon Linux 2023: installs Docker, clones the repo and starts the app.
# Edit REPO_URL, then paste into "Advanced details → User data" when launching the instance.
# After boot: ssh in, put your secrets in /opt/graph-rag/.env, then `docker compose up -d --build`.
set -euxo pipefail

REPO_URL="https://github.com/KorraSanthosh/graph-rag-code-refactoring-engine.git"

dnf install -y docker git
systemctl enable --now docker

# docker compose v2 plugin
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

git clone "$REPO_URL" /opt/graph-rag
cd /opt/graph-rag
cp .env.example .env
docker pull python:3.11-slim   # pre-pull the sandbox image so first request isn't slow
echo "Now edit /opt/graph-rag/.env (OPENAI_API_KEY, ACCESS_KEY) and run: docker compose up -d --build"
