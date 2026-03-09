"""
Comprehensive tests for delivery views
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from django.contrib.auth import get_user_model
from rest_framework import status
from deliveries.models import Delivery, Biker, DeliveryAssignment, DeliveryLocation, DeliveryLog

User = get_user_model()


@pytest.mark.django_db
class TestDeliveryViewSetList:
    """Test delivery list endpoint permissions and filtering"""
    
    def test_admin_sees_all_deliveries(self, admin_client, client_user):
        """Admin can see all deliveries"""
        api_client, _ = admin_client
        
        # Create deliveries from different clients
        Delivery.objects.create(
            client=client_user,
            pickup_address='Address 1',
            dropoff_address='Address 2',
            package_description='Package 1'
        )
        
        other_user = User.objects.create_user(
            email='other@example.com',
            password='pass123',
            role='CLIENT'
        )
        Delivery.objects.create(
            client=other_user,
            pickup_address='Address 3',
            dropoff_address='Address 4',
            package_description='Package 2'
        )
        
        response = api_client.get('/api/deliveries/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
    
    def test_client_sees_only_own_deliveries(self, client_api_client, client_user):
        """Client can only see their own deliveries"""
        api_client, user = client_api_client
        
        # Create own delivery
        Delivery.objects.create(
            client=user,
            pickup_address='My Address',
            dropoff_address='Destination',
            package_description='My package'
        )
        
        # Create another user's delivery
        other_user = User.objects.create_user(
            email='other@example.com',
            password='pass123',
            role='CLIENT'
        )
        Delivery.objects.create(
            client=other_user,
            pickup_address='Other Address',
            dropoff_address='Other Dest',
            package_description='Other package'
        )
        
        response = api_client.get('/api/deliveries/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['pickup_address'] == 'My Address'
    
    def test_biker_sees_searching_and_assigned_deliveries(self, biker_client, biker_user, client_user):
        """Biker sees SEARCHING deliveries and their assigned deliveries"""
        api_client, user = biker_client
        _, biker = biker_user
        
        # Create a SEARCHING delivery (biker should see)
        searching = Delivery.objects.create(
            client=client_user,
            pickup_address='Searching Address',
            dropoff_address='Dest',
            package_description='Package',
            status='SEARCHING'
        )
        
        # Create an assigned delivery for this biker
        assigned = Delivery.objects.create(
            client=client_user,
            pickup_address='Assigned Address',
            dropoff_address='Dest',
            package_description='Package',
            status='ASSIGNED'
        )
        DeliveryAssignment.objects.create(delivery=assigned, biker=biker, accepted=True)
        
        # Create a PENDING delivery (biker should NOT see)
        Delivery.objects.create(
            client=client_user,
            pickup_address='Pending Address',
            dropoff_address='Dest',
            package_description='Package',
            status='PENDING'
        )
        
        response = api_client.get('/api/deliveries/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


@pytest.mark.django_db
class TestDeliveryViewSetCreate:
    """Test delivery creation endpoint"""
    
    @patch('deliveries.views.delivery_views.get_channel_layer')
    @patch('deliveries.views.delivery_views.find_nearby_bikers')
    def test_create_delivery_sets_status_to_searching(
        self, mock_find_bikers, mock_channel_layer, client_api_client
    ):
        """Creating a delivery sets status to SEARCHING"""
        mock_find_bikers.return_value = []
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        api_client, _ = client_api_client
        
        response = api_client.post('/api/deliveries/', {
            'pickup_address': '123 Main St',
            'dropoff_address': '456 Oak Ave',
            'package_description': 'Test package',
            'pickup_latitude': -26.2041,
            'pickup_longitude': 28.0473
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        delivery = Delivery.objects.get(id=response.data['id'])
        assert delivery.status == 'SEARCHING'
    
    @patch('deliveries.views.delivery_views.get_channel_layer')
    @patch('deliveries.views.delivery_views.find_nearby_bikers')
    def test_create_delivery_notifies_nearby_bikers(
        self, mock_find_bikers, mock_channel_layer, client_api_client, biker_user
    ):
        """Creating a delivery sends WebSocket notification to nearby bikers"""
        _, biker = biker_user
        mock_find_bikers.return_value = [biker]
        
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        api_client, _ = client_api_client
        
        response = api_client.post('/api/deliveries/', {
            'pickup_address': '123 Main St',
            'dropoff_address': '456 Oak Ave',
            'package_description': 'Test package',
            'pickup_latitude': -26.2041,
            'pickup_longitude': 28.0473
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        mock_find_bikers.assert_called_once()
    
    def test_create_delivery_requires_auth(self, api_client):
        """Unauthenticated users cannot create deliveries"""
        response = api_client.post('/api/deliveries/', {
            'pickup_address': '123 Main St',
            'dropoff_address': '456 Oak Ave',
            'package_description': 'Test package'
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDeliveryViewSetAssign:
    """Test delivery assignment endpoint"""
    
    def test_admin_can_assign_biker(self, admin_client, client_user, biker_user):
        """Admin can assign a biker to a delivery"""
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
        assert 'assignment_id' in response.data
        
        delivery.refresh_from_db()
        assert delivery.status == 'ASSIGNED'
    
    def test_assign_requires_biker_id(self, admin_client, client_user):
        """Assignment requires biker_id parameter"""
        api_client, _ = admin_client
        
        delivery = Delivery.objects.create(
            client=client_user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package'
        )
        
        response = api_client.post(f'/api/deliveries/{delivery.id}/assign/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'biker_id' in response.data['error']
    
    def test_assign_invalid_biker(self, admin_client, client_user):
        """Assignment with invalid biker_id returns 404"""
        api_client, _ = admin_client
        
        delivery = Delivery.objects.create(
            client=client_user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package'
        )
        
        response = api_client.post(f'/api/deliveries/{delivery.id}/assign/', {
            'biker_id': 99999
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_non_admin_cannot_assign(self, client_api_client, client_user, biker_user):
        """Non-admin users cannot assign bikers"""
        api_client, _ = client_api_client
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
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDeliveryViewSetAccept:
    """Test delivery accept endpoint"""
    
    @patch('deliveries.views.delivery_views.accept_delivery')
    def test_biker_can_accept_delivery(self, mock_accept, biker_client, biker_user, searching_delivery):
        """Biker can accept a SEARCHING delivery"""
        api_client, user = biker_client
        _, biker = biker_user
        
        mock_assignment = MagicMock()
        mock_accept.return_value = mock_assignment
        
        response = api_client.post(f'/api/deliveries/{searching_delivery.id}/accept/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['message'] == 'Delivery accepted'
        mock_accept.assert_called_once()
    
    @patch('deliveries.views.delivery_views.accept_delivery')
    def test_accept_already_assigned_returns_error(self, mock_accept, biker_client, searching_delivery):
        """Accepting already assigned delivery returns error"""
        api_client, _ = biker_client
        mock_accept.return_value = None
        
        response = api_client.post(f'/api/deliveries/{searching_delivery.id}/accept/')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'already assigned' in response.data['error']


@pytest.mark.django_db
class TestDeliveryViewSetMarkDelivered:
    """Test mark_delivered endpoint"""
    
    @patch('deliveries.views.delivery_views.get_channel_layer')
    def test_assigned_biker_can_mark_delivered(self, mock_channel_layer, client_user, biker_user):
        """Assigned biker can mark delivery as delivered"""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        user, biker = biker_user
        
        # Create delivery with assignment
        delivery = Delivery.objects.create(
            client=client_user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package',
            pickup_latitude=-26.2041,
            pickup_longitude=28.0473,
            status='IN_TRANSIT'
        )
        assignment = DeliveryAssignment.objects.create(
            delivery=delivery,
            biker=biker,
            accepted=True
        )
        
        # Create API client for biker
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        
        api_client = APIClient()
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        response = api_client.post(f'/api/deliveries/{delivery.id}/mark_delivered/')
        
        assert response.status_code == status.HTTP_200_OK
        
        delivery.refresh_from_db()
        assert delivery.status == 'DELIVERED'
        
        biker.refresh_from_db()
        assert biker.status == 'AVAILABLE'
        
        assert DeliveryLog.objects.filter(delivery=delivery).exists()
    
    def test_unassigned_delivery_returns_error(self, biker_client, client_user):
        """Marking unassigned delivery returns error"""
        api_client, _ = biker_client
        
        delivery = Delivery.objects.create(
            client=client_user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package',
            status='SEARCHING'
        )
        
        response = api_client.post(f'/api/deliveries/{delivery.id}/mark_delivered/')
        # Should return 404 because biker doesn't see SEARCHING deliveries they're not assigned to
        # or 400 if they can see it but it's not assigned
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]
    
    @patch('deliveries.views.delivery_views.get_channel_layer')
    def test_wrong_biker_cannot_mark_delivered(self, mock_channel_layer, client_user, biker_user):
        """Biker not assigned to delivery cannot mark as delivered"""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        user, biker = biker_user
        
        # Create delivery assigned to a different biker
        other_biker_user = User.objects.create_user(
            email='assigned_biker@example.com',
            password='pass123',
            role='BIKER'
        )
        assigned_biker = Biker.objects.create(user=other_biker_user, status='ON_DELIVERY')
        
        delivery = Delivery.objects.create(
            client=client_user,
            pickup_address='123 Main St',
            dropoff_address='456 Oak Ave',
            package_description='Package',
            pickup_latitude=-26.2041,
            pickup_longitude=28.0473,
            status='IN_TRANSIT'
        )
        DeliveryAssignment.objects.create(
            delivery=delivery,
            biker=assigned_biker,
            accepted=True
        )
        
        # Create API client for wrong biker (the fixture biker)
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        
        api_client = APIClient()
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        response = api_client.post(f'/api/deliveries/{delivery.id}/mark_delivered/')
        # Should return 404 (can't see) or 403 (forbidden)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]


@pytest.mark.django_db
class TestDeliveryViewSetMyDeliveries:
    """Test my_deliveries endpoint"""
    
    def test_my_deliveries_returns_stats(self, client_api_client, client_user):
        """my_deliveries returns delivery stats"""
        api_client, user = client_api_client
        
        Delivery.objects.create(
            client=user, pickup_address='A', dropoff_address='B',
            package_description='P', status='PENDING'
        )
        Delivery.objects.create(
            client=user, pickup_address='C', dropoff_address='D',
            package_description='P', status='IN_TRANSIT'
        )
        Delivery.objects.create(
            client=user, pickup_address='E', dropoff_address='F',
            package_description='P', status='DELIVERED'
        )
        
        response = api_client.get('/api/deliveries/my_deliveries/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['stats']['total'] == 3
        assert response.data['stats']['pending'] == 1
        assert response.data['stats']['in_transit'] == 1
        assert response.data['stats']['delivered'] == 1
        assert len(response.data['deliveries']) == 3


@pytest.mark.django_db
class TestAssignmentViewSet:
    """Test assignment viewset"""
    
    def test_admin_can_list_assignments(self, admin_client, assigned_delivery):
        """Admin can list all assignments"""
        api_client, _ = admin_client
        
        response = api_client.get('/api/assignments/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
    
    def test_non_admin_cannot_list_assignments(self, client_api_client):
        """Non-admin cannot access assignments"""
        api_client, _ = client_api_client
        
        response = api_client.get('/api/assignments/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestLocationViewSet:
    """Test location viewset"""
    
    def test_biker_can_list_own_locations(self, biker_client, assigned_delivery, biker_user):
        """Biker can list locations for their deliveries"""
        api_client, _ = biker_client
        delivery = assigned_delivery  # assigned_delivery is now just a delivery object
        _, biker = biker_user
        
        DeliveryLocation.objects.create(
            delivery=delivery,
            biker=biker,
            latitude=-26.2041,
            longitude=28.0473
        )
        
        response = api_client.get('/api/locations/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
