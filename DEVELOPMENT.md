# Development Guide

## Setup

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Git

### Installation

```bash
# Clone repository
git clone <repo-url>
cd mforce_

# Configure environment
cp .env.example .env

# Start services
docker compose up -d

# Run migrations
docker compose exec backend python manage.py migrate

# Create superuser
docker compose exec backend python manage.py createsuperuser
```

## Configuration

### Environment Variables

```env
# Django
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=sqlite3
DB_NAME=db.sqlite3

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# JWT
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=1

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8001
```

### Database Options

**SQLite** (development):
```env
DB_ENGINE=sqlite3
DB_NAME=db.sqlite3
```

**PostgreSQL** (production):
```env
DB_ENGINE=postgresql
DB_NAME=mforce_db
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=db
DB_PORT=5432
```

## Testing

```bash
# Run all tests
docker compose exec backend pytest

# With coverage
docker compose exec backend pytest --cov=accounts --cov=deliveries

# Specific module
docker compose exec backend pytest accounts/tests/

# Verbose output
docker compose exec backend pytest -v
```

### Test Fixtures

- `api_client` - Unauthenticated client
- `authenticated_client` - Client user
- `admin_client` - Admin user
- `biker_client` - Biker user
- `clear_cache` - Cache cleanup

## Development Workflow

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver

# Start Redis (separate terminal)
redis-server
```

### Database Migrations

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Check status
python manage.py showmigrations
```

## Docker Commands

```bash
# Build
docker compose build

# Start
docker compose up -d

# Stop
docker compose down

# Logs
docker compose logs -f backend

# Execute command
docker compose exec backend <command>

# Rebuild
docker compose up -d --build
```

## Troubleshooting

### Port Conflict

```bash
# Find process
lsof -i :8001
kill -9 <PID>
```

### Redis Connection

```bash
# Check status
docker compose ps redis

# Restart
docker compose restart redis
```

### Migration Issues

```bash
# Check status
docker compose exec backend python manage.py showmigrations

# Rollback
docker compose exec backend python manage.py migrate app_name migration_number
```

## Production Deployment

### Setup

```bash
# Use production compose
docker compose -f docker-compose.prod.yml up -d

# Collect static files
docker compose exec backend python manage.py collectstatic

# Create superuser
docker compose exec backend python manage.py createsuperuser
```

### Production Checklist

- [ ] Secure `SECRET_KEY`
- [ ] `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use PostgreSQL
- [ ] Restrict `CORS_ALLOWED_ORIGINS`
- [ ] Configure email backend
- [ ] Set Redis password
- [ ] Configure SSL/TLS

## API Endpoints

### Authentication
- `POST /api/token/` - Obtain JWT tokens
- `POST /api/token/refresh/` - Refresh access token

### Deliveries
- `GET /api/deliveries/` - List deliveries
- `POST /api/deliveries/` - Create delivery
- `GET /api/deliveries/{id}/` - Get details
- `PATCH /api/deliveries/{id}/` - Update delivery
- `POST /api/deliveries/{id}/assign/` - Assign biker
- `POST /api/deliveries/{id}/mark_delivered/` - Mark delivered
- `GET /api/deliveries/my_deliveries/` - User stats

### System
- `GET /health/` - Health check

## Project Structure

```
force_backend/          - Django settings
accounts/               - Authentication
deliveries/             - Delivery management
  ├── consumers.py      - WebSocket handlers
  ├── models.py         - Data models
  ├── serializers.py    - API serializers
  ├── views.py          - API views
  ├── permissions.py    - Access control
  ├── location.py       - Location utilities
  └── tests/            - Test suite
```

## Contributing

1. Create feature branch
2. Make changes and add tests
3. Run test suite
4. Submit pull request
