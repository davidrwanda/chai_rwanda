#!/bin/bash
set -e

echo "=================================================="
echo "  Data Platform - Quick Start Script"
echo "=================================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

echo "✓ Docker is running"

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "✓ Created .env file"
fi

# Build all containers
echo ""
echo "Building Docker containers (this may take a few minutes)..."
docker compose build

echo ""
echo "✓ Build complete!"
echo ""
echo "=================================================="
echo "  Setup Complete! Next Steps:"
echo "=================================================="
echo ""
echo "1. Start services:"
echo "   make up"
echo ""
echo "2. Run the complete pipeline:"
echo "   make pipeline"
echo ""
echo "3. Access services:"
echo "   - Grafana:  http://localhost:3000 (admin/admin)"
echo "   - MLflow:   http://localhost:5000"
echo "   - MinIO:    http://localhost:9001 (minioadmin/minioadmin)"
echo ""
echo "=================================================="
