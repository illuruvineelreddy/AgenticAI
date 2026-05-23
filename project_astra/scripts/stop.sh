#!/bin/bash
# Project Astra - Stop Script

echo "Stopping all services..."
docker-compose down

echo ""
echo "Services stopped."
echo "To remove volumes (database data), run: docker-compose down -v"
