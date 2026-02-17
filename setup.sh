#!/bin/bash
# Force Backend Setup Script

set -e

echo "Force Backend - Initial Setup"
echo ""

# Check .env
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo ".env created. Please review and update if needed."
else
    echo ".env already exists"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not installed"
    exit 1
fi

# Check Docker Compose
if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose not available"
    exit 1
fi

# Build images
echo ""
echo "Building Docker images..."
docker compose build

# Start services
echo ""
echo "Starting services..."
docker compose up -d

# Wait for services
echo ""
echo "Waiting for services..."
sleep 5

# Run migrations
echo ""
echo "Running migrations..."
docker compose exec -T backend python manage.py migrate

# Create superuser
echo ""
echo "Create superuser account:"
docker compose exec backend python manage.py createsuperuser

# Complete
echo ""
echo "Setup complete!"
echo ""
echo "Services:"
echo "  API: http://localhost:8001"
echo "  Admin: http://localhost:8001/admin"
echo "  Health: http://localhost:8001/health"
echo ""
echo "Run tests: docker compose exec backend pytest"

