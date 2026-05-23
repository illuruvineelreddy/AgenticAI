@echo off
REM Quick Start Script for Agentic AI Trading Platform (Windows)
REM This script automates the local setup process

echo ==========================================
echo Agentic AI Trading Platform - Quick Start
echo ==========================================
echo.

REM Check if Docker is installed
echo Checking Docker installation...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)
echo [OK] Docker found

REM Check if Docker Compose is installed
echo Checking Docker Compose...
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    docker compose version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Docker Compose is not available.
        pause
        exit /b 1
    )
    set COMPOSE_CMD=docker compose
    echo [OK] Docker Compose found (new syntax)
) else (
    set COMPOSE_CMD=docker-compose
    echo [OK] Docker Compose found
)

REM Setup environment file
echo Setting up environment variables...
if exist .env (
    echo [INFO] .env file already exists. Skipping...
) else (
    if exist .env.example (
        copy .env.example .env
        echo [OK] Created .env from .env.example
    ) else (
        echo [ERROR] .env.example not found!
        pause
        exit /b 1
    )
)

REM Build and start services
echo Building and starting all services...
echo [INFO] This may take a few minutes on first run...
%COMPOSE_CMD% up -d --build
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start services. Check logs with: %COMPOSE_CMD% logs
    pause
    exit /b 1
)
echo [OK] All services started successfully!

REM Wait for services
echo Waiting for services to be ready...

REM Wait for PostgreSQL
echo Waiting for PostgreSQL...
for /l %%i in (1,1,30) do (
    docker-compose exec -T postgres pg_isready -U postgres >nul 2>&1
    if not errorlevel 1 (
        echo [OK] PostgreSQL is ready!
        goto :postgres_ready
    )
    timeout /t 2 /nobreak >nul
)
echo [WARN] PostgreSQL took longer than expected to start

:postgres_ready

REM Wait for Redis
echo Waiting for Redis...
for /l %%i in (1,1,30) do (
    docker-compose exec -T redis redis-cli ping >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Redis is ready!
        goto :redis_ready
    )
    timeout /t 2 /nobreak >nul
)
echo [WARN] Redis took longer than expected to start

:redis_ready

REM Wait for Backend
echo Waiting for Backend API...
for /l %%i in (1,1,60) do (
    curl -s http://localhost:8000/api/health >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Backend API is ready!
        goto :backend_ready
    )
    timeout /t 2 /nobreak >nul
)
echo [WARN] Backend took longer than expected to start

:backend_ready

REM Initialize database
echo Initializing database...
docker-compose exec -T backend python -m database.init_db
if %errorlevel% equ 0 (
    echo [OK] Database initialized successfully!
) else (
    echo [WARN] Database initialization may have already been done or failed
)

REM Show status
echo.
echo ==========================================
echo [SUCCESS] Setup Complete!
echo ==========================================
echo.
echo Services Status:
echo ----------------
docker-compose ps
echo.
echo Access Points:
echo --------------
echo Frontend Dashboard:  http://localhost:3000
echo Backend API:          http://localhost:8000
echo API Documentation:    http://localhost:8000/docs
echo Grafana:              http://localhost:3001 (admin/admin)
echo Prometheus:           http://localhost:9090
echo.
echo Next Steps:
echo -----------
echo 1. Open dashboard: http://localhost:3000
echo 2. Test API: curl http://localhost:8000/api/health
echo 3. View logs: docker-compose logs -f
echo 4. Start replay: docker-compose exec backend python -m replay_engine.start_replay --speed 10x
echo.
echo To stop all services:
echo   docker-compose down
echo.
pause
