"""
Tests for deliveries app models and views
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from deliveries.models import Delivery, Biker, DeliveryAssignment, DeliveryLocation

User = get_user_model()


@pytest.mark.django_db
class TestBikerModel:
    """Test Biker model"""
    
    def test_create_biker(self, biker_user):
        """Test creating a biker"""
        user, biker = biker_user
        assert biker.user == user
        assert biker.status == 'AVAILABLE'
        assert biker.phone_number == '+1234567890'
    
    def test_biker_str_representation(self, biker_user):
        """Test biker string representation"""
        _, biker = biker_user
        expected = f"Biker: {biker.user.email} (AVAILABLE)"
        assert str(biker) == expected
    
    def test_biker_status_choices(self):
        """Test biker status choices"""
        user = User.objects.create_user(
            email='biker@example.com',
            password='pass123',
            role='BIKER'
        )
        biker = Biker.objects.create(user=user, status='ON_DELIVERY')
        assert biker.status == 'ON_DELIVERY'


@pytest.mark.django_db
class TestDeliveryModel:
    """Test Delivery model"""
    
    def test_create_delivery(self, client_user):
        """Test creating a delivery"""
        delivery = Delivery.objects.create(
            client=client_user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package contents',
            status='PENDING'
        )
        assert delivery.client == client_user
        assert delivery.status == 'PENDING'
        assert delivery.pickup_address == '123 Main St'
    
    def test_delivery_status_choices(self, client_user):
        """Test delivery status progression"""
        delivery = Delivery.objects.create(
            client=client_user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package',
        )
        assert delivery.status == 'PENDING'
        
        delivery.status = 'ASSIGNED'
        delivery.save()
        delivery.refresh_from_db()
        assert delivery.status == 'ASSIGNED'
    
    def test_delivery_str_representation(self, client_user):
        """Test delivery string representation"""
        delivery = Delivery.objects.create(
            client=client_user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package',
            status='IN_TRANSIT'
        )
        assert 'IN_TRANSIT' in str(delivery)


@pytest.mark.django_db
class TestDeliveryAssignment:
    """Test DeliveryAssignment model"""
    
    def test_create_assignment(self, client_user, biker_user):
        """Test creating a delivery assignment"""
        delivery = Delivery.objects.create(
            client=client_user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package',
        )
        _, biker = biker_user
        
        assignment = DeliveryAssignment.objects.create(
            delivery=delivery,
            biker=biker,
            accepted=True
        )
        assert assignment.delivery == delivery
        assert assignment.biker == biker
        assert assignment.accepted


@pytest.mark.django_db
class TestDeliveryLocation:
    """Test DeliveryLocation model"""
    
    def test_create_location(self, client_user, biker_user):
        """Test creating a delivery location"""
        delivery = Delivery.objects.create(
            client=client_user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package',
        )
        _, biker = biker_user
        
        location = DeliveryLocation.objects.create(
            delivery=delivery,
            biker=biker,
            latitude=40.7128,
            longitude=-74.0060
        )
        assert location.latitude == 40.7128
        assert location.longitude == -74.0060


@pytest.mark.django_db
class TestDeliveryViewSet:
    """Test Delivery API endpoints"""
    
    def test_list_deliveries_as_client(self, client_api_client, client_user):
        """Test listing deliveries as client"""
        api_client, user = client_api_client
        
        # Create a delivery for the client
        Delivery.objects.create(
            client=user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package'
        )
        
        response = api_client.get('/api/deliveries/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
    
    def test_create_delivery_as_client(self, client_api_client):
        """Test creating a delivery as client"""
        api_client, _ = client_api_client
        
        response = api_client.post('/api/deliveries/', {
            'pickup_address': '123 Main St',
            'dropoff_address': '456 Oak Ave',
            'package_description': 'A package'
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Delivery.objects.count() == 1
    
    def test_list_deliveries_without_auth(self, api_client):
        """Test that unauthenticated users cannot access deliveries"""
        response = api_client.get('/api/deliveries/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_assign_delivery_as_admin(self, admin_client, client_user, biker_user):
        """Test assigning delivery as admin"""
        api_client, _ = admin_client
        _, biker = biker_user
        
        delivery = Delivery.objects.create(
            client=client_user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package'
        )
        
        response = api_client.post(f'/api/deliveries/{delivery.id}/assign/', {
            'biker_id': biker.id
        })
        assert response.status_code == status.HTTP_200_OK
        
        delivery.refresh_from_db()
        assert delivery.status == 'ASSIGNED'
