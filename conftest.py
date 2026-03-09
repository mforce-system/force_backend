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


@pytest.fixture
def delivery(client_user):
    """Create a basic delivery"""
    from deliveries.models import Delivery
    return Delivery.objects.create(
        client=client_user,
        pickup_address='123 Main St',
        dropoff_address='456 Oak Ave',
        package_description='Test package',
        pickup_latitude=-26.2041,
        pickup_longitude=28.0473,
        status='PENDING'
    )


@pytest.fixture
def searching_delivery(client_user):
    """Create a delivery in SEARCHING status"""
    from deliveries.models import Delivery
    return Delivery.objects.create(
        client=client_user,
        pickup_address='123 Main St',
        dropoff_address='456 Oak Ave',
        package_description='Test package',
        pickup_latitude=-26.2041,
        pickup_longitude=28.0473,
        status='SEARCHING'
    )


@pytest.fixture
def assigned_delivery(client_user, biker_user):
    """Create an assigned delivery with biker"""
    from deliveries.models import Delivery, DeliveryAssignment
    _, biker_obj = biker_user
    delivery_obj = Delivery.objects.create(
        client=client_user,
        pickup_address='123 Main St',
        dropoff_address='456 Oak Ave',
        package_description='Test package',
        pickup_latitude=-26.2041,
        pickup_longitude=28.0473,
        status='ASSIGNED'
    )
    assignment = DeliveryAssignment.objects.create(
        delivery=delivery_obj,
        biker=biker_obj,
        accepted=True
    )
    delivery_obj.assignment = assignment
    return delivery_obj


@pytest.fixture
def biker(biker_user):
    """Get the biker object from biker_user fixture"""
    _, biker_obj = biker_user
    return biker_obj


@pytest.fixture
def biker_with_location(biker_user):
    """Create a biker with location data"""
    user, biker_obj = biker_user
    biker_obj.current_latitude = -26.2050
    biker_obj.current_longitude = 28.0480
    biker_obj.save()
    return biker_obj


@pytest.fixture
def delivery_with_assignment(client_user, biker_user):
    """Create a delivery with assignment"""
    from deliveries.models import Delivery, DeliveryAssignment
    _, biker_obj = biker_user
    delivery_obj = Delivery.objects.create(
        client=client_user,
        pickup_address='123 Main St',
        dropoff_address='456 Oak Ave',
        package_description='Test package',
        pickup_latitude=-26.2041,
        pickup_longitude=28.0473,
        status='ASSIGNED'
    )
    assignment = DeliveryAssignment.objects.create(
        delivery=delivery_obj,
        biker=biker_obj,
        accepted=True
    )
    delivery_obj.assignment = assignment  # Attach for easy access
    return delivery_obj


@pytest.fixture
def delivery_with_location(client_user, biker_user):
    """Create a delivery with location tracking"""
    from deliveries.models import Delivery, DeliveryAssignment, DeliveryLocation
    _, biker_obj = biker_user
    delivery_obj = Delivery.objects.create(
        client=client_user,
        pickup_address='123 Main St',
        dropoff_address='456 Oak Ave',
        package_description='Test package',
        pickup_latitude=-26.2041,
        pickup_longitude=28.0473,
        status='IN_TRANSIT'
    )
    assignment = DeliveryAssignment.objects.create(
        delivery=delivery_obj,
        biker=biker_obj,
        accepted=True
    )
    DeliveryLocation.objects.create(
        delivery=delivery_obj,
        biker=biker_obj,
        latitude=-26.2045,
        longitude=28.0478
    )
    delivery_obj.assignment = assignment
    return delivery_obj


@pytest.fixture
def multiple_bikers():
    """Create multiple bikers for testing nearby bikers functionality"""
    from deliveries.models import Biker
    bikers = []
    for i in range(5):
        user = User.objects.create_user(
            email=f'biker{i}@example.com',
            password='bikerpass123',
            role='BIKER'
        )
        biker_obj = Biker.objects.create(
            user=user,
            status='AVAILABLE',
            current_latitude=-26.2041 + (i * 0.001),  # Slightly different locations
            current_longitude=28.0473 + (i * 0.001)
        )
        bikers.append(biker_obj)
    return bikers


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache between tests"""
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()
