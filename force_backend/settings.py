from pathlib import Path
from datetime import timedelta
from .config import get_config

BASE_DIR = Path(__file__).resolve().parent.parent

# Load configuration from environment
config = get_config()

SECRET_KEY = config.SECRET_KEY
DEBUG = config.DEBUG
ALLOWED_HOSTS = config.ALLOWED_HOSTS

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework.authtoken',
    'channels',
    'corsheaders',
    'accounts',
    'deliveries',

]

ASGI_APPLICATION = "force_backend.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(config.REDIS_HOST, config.REDIS_PORT)],
        },
    },
}

AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=config.JWT_ACCESS_TOKEN_LIFETIME_MINUTES),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config.JWT_REFRESH_TOKEN_LIFETIME_DAYS),
    "AUTH_HEADER_TYPES": ("Bearer",),
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'force_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'force_backend.wsgi.application'

# Database configuration - modular for easy switching
def _get_database_config():
    """Build database config based on environment"""
    if config.DB_ENGINE == 'sqlite3':
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': config.DB_NAME,
        }
    elif config.DB_ENGINE == 'postgresql':
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config.DB_NAME,
            'USER': config.DB_USER,
            'PASSWORD': config.DB_PASSWORD,
            'HOST': config.DB_HOST,
            'PORT': config.DB_PORT,
            'CONN_MAX_AGE': 600,
        }
    else:
        raise ValueError(f"Unsupported database engine: {config.DB_ENGINE}")

DATABASES = {
    'default': _get_database_config()
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
APPEND_SLASH = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS Configuration
CORS_ALLOWED_ORIGINS = config.CORS_ALLOWED_ORIGINS
CORS_ALLOW_CREDENTIALS = True

# Email Configuration
EMAIL_BACKEND = config.EMAIL_BACKEND
EMAIL_HOST = config.EMAIL_HOST
EMAIL_PORT = config.EMAIL_PORT
EMAIL_HOST_USER = config.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = config.EMAIL_HOST_PASSWORD
EMAIL_USE_TLS = config.EMAIL_USE_TLS
DEFAULT_FROM_EMAIL = config.DEFAULT_FROM_EMAIL

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'deliveries': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
LOGS_DIR = BASE_DIR / 'logs'
os.makedirs(LOGS_DIR, exist_ok=True)
