#!/bin/bash

# Quick Start Script for Agentic AI Trading Platform
# This script automates the local setup process

set -e  # Exit on error

echo "=========================================="
echo "Agentic AI Trading Platform - Quick Start"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "→ $1"
}

# Check if Docker is installed
check_docker() {
    print_info "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker Desktop first."
        exit 1
    fi
    print_success "Docker found: $(docker --version)"
}

# Check if Docker Compose is available
check_docker_compose() {
    print_info "Checking Docker Compose..."
    if ! command -v docker-compose &> /dev/null; then
        # Try docker compose (new syntax)
        if ! docker compose version &> /dev/null; then
            print_error "Docker Compose is not available."
            exit 1
        fi
        COMPOSE_CMD="docker compose"
        print_success "Docker Compose found (new syntax)"
    else
        COMPOSE_CMD="docker-compose"
        print_success "Docker Compose found: $(docker-compose --version)"
    fi
}

# Setup environment file
setup_env() {
    print_info "Setting up environment variables..."
    if [ -f .env ]; then
        print_warning ".env file already exists. Skipping..."
    else
        if [ -f .env.example ]; then
            cp .env.example .env
            print_success "Created .env from .env.example"
        else
            print_error ".env.example not found!"
            exit 1
        fi
    fi
}

# Build and start services
start_services() {
    print_info "Building and starting all services..."
    print_warning "This may take a few minutes on first run..."
    
    $COMPOSE_CMD up -d --build
    
    if [ $? -eq 0 ]; then
        print_success "All services started successfully!"
    else
        print_error "Failed to start services. Check logs with: $COMPOSE_CMD logs"
        exit 1
    fi
}

# Wait for services to be healthy
wait_for_services() {
    print_info "Waiting for services to be ready..."
    
    # Wait for PostgreSQL
    print_info "Waiting for PostgreSQL..."
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U postgres &> /dev/null 2>&1; then
            print_success "PostgreSQL is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "PostgreSQL took longer than expected to start"
        fi
        sleep 2
    done
    
    # Wait for Redis
    print_info "Waiting for Redis..."
    for i in {1..30}; do
        if docker-compose exec -T redis redis-cli ping &> /dev/null 2>&1; then
            print_success "Redis is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            print_warning "Redis took longer than expected to start"
        fi
        sleep 2
    done
    
    # Wait for Backend
    print_info "Waiting for Backend API..."
    for i in {1..60}; do
        if curl -s http://localhost:8000/api/health &> /dev/null; then
            print_success "Backend API is ready!"
            break
        fi
        if [ $i -eq 60 ]; then
            print_warning "Backend took longer than expected to start"
        fi
        sleep 2
    done
}

# Initialize database
init_database() {
    print_info "Initializing database..."
    docker-compose exec -T backend python -m database.init_db
    
    if [ $? -eq 0 ]; then
        print_success "Database initialized successfully!"
    else
        print_warning "Database initialization may have already been done or failed"
    fi
}

# Show status
show_status() {
    echo ""
    echo "=========================================="
    print_success "Setup Complete!"
    echo "=========================================="
    echo ""
    echo "Services Status:"
    echo "----------------"
    docker-compose ps
    echo ""
    echo "Access Points:"
    echo "--------------"
    echo -e "${GREEN}Frontend Dashboard:${NC}  http://localhost:3000"
    echo -e "${GREEN}Backend API:${NC}          http://localhost:8000"
    echo -e "${GREEN}API Documentation:${NC}    http://localhost:8000/docs"
    echo -e "${GREEN}Grafana:${NC}              http://localhost:3001 (admin/admin)"
    echo -e "${GREEN}Prometheus:${NC}           http://localhost:9090"
    echo ""
    echo "Next Steps:"
    echo "-----------"
    echo "1. Open dashboard: http://localhost:3000"
    echo "2. Test API: curl http://localhost:8000/api/health"
    echo "3. View logs: docker-compose logs -f"
    echo "4. Start replay: docker-compose exec backend python -m replay_engine.start_replay --speed 10x"
    echo ""
    echo "To stop all services:"
    echo "  docker-compose down"
    echo ""
}

# Main execution
main() {
    check_docker
    check_docker_compose
    setup_env
    start_services
    wait_for_services
    init_database
    show_status
}

# Run main function
main
