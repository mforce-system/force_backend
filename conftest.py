"""
Pytest fixtures for testing
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture
def api_client():
    """Provide API client for tests"""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client):
    """Provide authenticated API client"""
    user = User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        role='CLIENT'
    )
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client, user


@pytest.fixture
def admin_user():
    """Create admin user"""
    user = User.objects.create_user(
        email='admin@example.com',
        password='adminpass123',
        role='ADMIN',
        is_staff=True,
        is_superuser=True
    )
    return user


@pytest.fixture
def admin_client(api_client, admin_user):
    """Provide authenticated API client with admin privileges"""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client, admin_user


@pytest.fixture
def biker_user():
    """Create biker user"""
    from deliveries.models import Biker
    
    user = User.objects.create_user(
        email='biker@example.com',
        password='bikerpass123',
        role='BIKER'
    )
    biker = Biker.objects.create(
        user=user,
        phone_number='+1234567890',
        status='AVAILABLE'
    )
    return user, biker


@pytest.fixture
def biker_client(api_client, biker_user):
    """Provide authenticated API client as biker"""
    user, _ = biker_user
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client, user


@pytest.fixture
def client_user():
    """Create regular client user"""
    user = User.objects.create_user(
        email='client@example.com',
        password='clientpass123',
        role='CLIENT'
    )
    return user


@pytest.fixture
def client_api_client(api_client, client_user):
    """Provide authenticated API client as regular client"""
    refresh = RefreshToken.for_user(client_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client, client_user


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache between tests"""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()
