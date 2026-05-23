#!/bin/bash
# Project Astra - Start Script

set -e

echo "=========================================="
echo "Project Astra - Starting Services"
echo "=========================================="

cd "$(dirname "$0")/.."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Start all services
echo "Starting Docker Compose services..."
docker-compose up -d

echo ""
echo "Waiting for services to be ready..."
sleep 10

# Check service health
echo ""
echo "Service Status:"
docker-compose ps

echo ""
echo "=========================================="
echo "Services Started Successfully!"
echo "=========================================="
echo ""
echo "Access URLs:"
echo "  Backend API:   http://localhost:8000"
echo "  Frontend:      http://localhost:3000"
echo "  Grafana:       http://localhost:3001 (admin/admin123)"
echo "  Prometheus:    http://localhost:9090"
echo ""
echo "View logs with: docker-compose logs -f"
echo "Stop with:      docker-compose down"
echo ""
