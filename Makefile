.PHONY: help build up down logs shell migrate test clean

help:
	@echo "Force Backend - Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make build              Build Docker images"
	@echo "  make up                 Start services"
	@echo ""
	@echo "Development:"
	@echo "  make logs               View logs"
	@echo "  make shell              Django shell"
	@echo "  make down               Stop services"
	@echo ""
	@echo "Database:"
	@echo "  make migrate            Run migrations"
	@echo "  make makemigrations     Create migrations"
	@echo "  make createsuperuser    Create admin user"
	@echo ""
	@echo "Testing:"
	@echo "  make test               Run tests"
	@echo "  make test-cov           Tests with coverage"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean              Remove containers"
	@echo "  make restart            Restart backend"

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f backend

shell:
	docker compose exec backend python manage.py shell

migrate:
	docker compose exec backend python manage.py migrate

makemigrations:
	docker compose exec backend python manage.py makemigrations

createsuperuser:
	docker compose exec backend python manage.py createsuperuser

test:
	docker compose exec backend pytest

test-cov:
	docker compose exec backend pytest --cov=accounts --cov=deliveries --cov-report=term-missing

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

restart:
	docker compose restart backend

