# Force Backend

Django REST API for delivery management system with real-time tracking.

## Quick Start

```bash
# Start services
docker compose up -d

# Run migrations
docker compose exec backend python manage.py migrate

# Create superuser
docker compose exec backend python manage.py createsuperuser

# Run tests
docker compose exec backend pytest
```

## Services

- API: http://localhost:8001
- Admin: http://localhost:8001/admin
- Health: http://localhost:8001/health

## Architecture

- Django 4.2.8 + Django REST Framework
- WebSocket support via Django Channels + Redis
- JWT authentication
- Role-based access control (Admin, Biker, Client)
- PostgreSQL/SQLite database support

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Key settings:
- `ENVIRONMENT` - development/testing/production
- `DB_ENGINE` - sqlite/postgresql
- `SECRET_KEY` - Django secret key
- `DEBUG` - Enable/disable debug mode
- `ALLOWED_HOSTS` - Comma-separated host list

## Database

Development uses SQLite by default. For PostgreSQL:

1. Update `.env`:
   ```
   DB_ENGINE=postgresql
   DB_NAME=mforce_db
   DB_USER=postgres
   DB_PASSWORD=yourpassword
   DB_HOST=db
   DB_PORT=5432
   ```

2. Run migrations:
   ```bash
   docker compose exec backend python manage.py migrate
   ```

## Testing

```bash
# Run all tests
docker compose exec backend pytest

# With coverage
docker compose exec backend pytest --cov=accounts --cov=deliveries

# Specific module
docker compose exec backend pytest accounts/tests/
```

## API Endpoints

### Authentication
- `POST /api/token/` - Obtain JWT token
- `POST /api/token/refresh/` - Refresh JWT token

### Deliveries
- `GET /api/deliveries/` - List deliveries
- `POST /api/deliveries/` - Create delivery
- `GET /api/deliveries/{id}/` - Get delivery details
- `POST /api/deliveries/{id}/assign/` - Assign biker (admin)
- `POST /api/deliveries/{id}/mark_delivered/` - Mark as delivered
- `GET /api/deliveries/my_deliveries/` - Get user deliveries with stats

### WebSocket
- `ws://localhost:8001/ws/tracking/{delivery_id}/?token={jwt_token}` - Real-time tracking

## Development

```bash
# View logs
docker compose logs -f backend

# Shell access
docker compose exec backend python manage.py shell

# Create migration
docker compose exec backend python manage.py makemigrations

# Run migration
docker compose exec backend python manage.py migrate
```

## Project Structure

```
force_backend/          - Django project settings
accounts/               - User authentication
deliveries/             - Delivery management
  ├── consumers.py      - WebSocket consumers
  ├── models.py         - Data models
  ├── serializers.py    - API serializers
  ├── views.py          - API views
  ├── permissions.py    - Access control
  └── tests/            - Test suite
```

## Documentation

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed development guide.

```
mforce_/
├── Dockerfile              # Production image
├── Dockerfile.dev          # Development image
├── docker-compose.yml      # Dev environment
├── docker-compose.prod.yml # Prod environment
├── requirements.txt        # Dependencies
├── force_backend/          # Core Django project
├── accounts/               # User authentication
├── deliveries/             # Delivery management
└── tests/                  # Test suites
```

## Environment Variables

```
ENVIRONMENT=development
SECRET_KEY=your-secret-key
DEBUG=True
DB_ENGINE=sqlite3
REDIS_HOST=localhost
REDIS_PORT=6379
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

See `.env.example` for all available options.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/token/` | Get JWT tokens |
| POST | `/api/token/refresh/` | Refresh access token |
| GET | `/api/deliveries/` | List deliveries |
| POST | `/api/deliveries/` | Create delivery |
| POST | `/api/deliveries/<id>/assign/` | Assign biker |
| GET | `/health/` | Health check |

## WebSocket

```
ws://localhost:8000/ws/delivery/<delivery_id>/
```

## Support

- 📖 Read [DEVELOPMENT.md](DEVELOPMENT.md) for detailed guides
- 🧪 Run tests: `make test`
- 🐛 Check logs: `make logs`
- ✅ Health check: `curl http://localhost:8000/health/`

## License

MIT

## Future Enhancements

- PostgreSQL integration (modular, ready)
- Celery for async tasks
- Advanced monitoring
- API rate limiting
- Mobile app support
- Payment integration
