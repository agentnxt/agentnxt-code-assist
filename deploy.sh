#!/bin/bash
# Deploy AGenNext Code Assist
# Usage: ./deploy.sh [--skip-build]

set -e

SKIP_BUILD=false
if [ "$1" == "--skip-build" ]; then
  SKIP_BUILD=true
fi

echo "=== Deploying AGenNext Code Assist ==="

# Build if not skipped
if [ "$SKIP_BUILD" == "false" ]; then
  echo "Building Docker image..."
  docker compose build
fi

# Start application
echo "Starting service..."
docker compose up -d

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Service:"
echo "  API:     http://localhost:8090"
echo "  Health:  http://localhost:8090/healthz"
echo ""
