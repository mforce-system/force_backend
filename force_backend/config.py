"""
Environment configuration module
Handles loading and validating environment variables
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / '.env'
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


class Config:
    """Base configuration"""
    # Django settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
    ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    
    # Database
    DB_ENGINE = os.getenv('DB_ENGINE', 'sqlite3')
    DB_NAME = os.getenv('DB_NAME', str(BASE_DIR / 'db.sqlite3'))
    DB_USER = os.getenv('DB_USER', '')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_HOST = os.getenv('DB_HOST', '')
    DB_PORT = os.getenv('DB_PORT', '')
    
    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
    
    # JWT
    JWT_ACCESS_TOKEN_LIFETIME_MINUTES = int(os.getenv('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', 60))
    JWT_REFRESH_TOKEN_LIFETIME_DAYS = int(os.getenv('JWT_REFRESH_TOKEN_LIFETIME_DAYS', 1))
    
    # Cors
    CORS_ALLOWED_ORIGINS = os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:3000,http://localhost:8000'
    ).split(',')
    
    # Email (for future use)
    EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
    EMAIL_HOST = os.getenv('EMAIL_HOST', '')
    EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
    EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
    EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@force.local')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ALLOWED_HOSTS = ['*']
    CORS_ALLOWED_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:8000',
        'http://localhost:8001',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:8000',
        'http://127.0.0.1:8001',
    ]
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    ALLOWED_HOSTS = ['*']
    CORS_ALLOWED_ORIGINS = ['http://127.0.0.1', 'http://localhost']
    DB_ENGINE = 'sqlite3'
    DB_NAME = ':memory:'
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # In production, ensure SECRET_KEY is set
    # and other critical settings are properly configured


def get_config():
    """Get configuration based on environment"""
    environment = os.getenv('ENVIRONMENT', 'development').lower()
    
    config_map = {
        'development': DevelopmentConfig,
        'dev': DevelopmentConfig,
        'testing': TestingConfig,
        'test': TestingConfig,
        'production': ProductionConfig,
        'prod': ProductionConfig,
    }
    
    return config_map.get(environment, DevelopmentConfig)()
