"""
Tests for the deliveries permissions module.
Tests IsAdmin, IsClientOwner, and IsAssignedBiker permission classes.
"""
import pytest
from unittest.mock import MagicMock, Mock
from django.contrib.auth import get_user_model
from deliveries.permissions import IsAdmin, IsClientOwner, IsAssignedBiker
from deliveries.models import Delivery, Biker, DeliveryAssignment

User = get_user_model()


@pytest.mark.django_db
class TestIsAdminPermission:
    """Tests for the IsAdmin permission class."""
    
    def test_admin_user_has_permission(self, admin_user):
        """Test that admin user has permission."""
        permission = IsAdmin()
        request = MagicMock()
        request.user = admin_user
        
        assert permission.has_permission(request, None) is True
    
    def test_staff_user_has_permission(self, admin_user):
        """Test that staff user (is_staff=True) has permission."""
        permission = IsAdmin()
        admin_user.is_staff = True
        admin_user.save()
        
        request = MagicMock()
        request.user = admin_user
        
        assert permission.has_permission(request, None) is True
    
    def test_client_user_does_not_have_permission(self, client_user):
        """Test that client user does not have permission."""
        permission = IsAdmin()
        request = MagicMock()
        request.user = client_user
        
        assert permission.has_permission(request, None) is False
    
    def test_biker_user_does_not_have_permission(self, biker_user):
        """Test that biker user does not have permission."""
        permission = IsAdmin()
        user, _ = biker_user  # biker_user fixture returns (user, biker)
        request = MagicMock()
        request.user = user
        
        assert permission.has_permission(request, None) is False
    
    def test_anonymous_user_does_not_have_permission(self):
        """Test that anonymous user does not have permission."""
        permission = IsAdmin()
        request = MagicMock()
        request.user = None
        
        # When user is None, the permission check should return falsy value
        result = permission.has_permission(request, None)
        assert not result  # Could be None or False


@pytest.mark.django_db
class TestIsClientOwnerPermission:
    """Tests for the IsClientOwner permission class."""
    
    def test_client_owns_delivery(self, client_user, delivery):
        """Test that client who owns delivery has permission."""
        permission = IsClientOwner()
        request = MagicMock()
        request.user = client_user
        
        # Ensure delivery belongs to client_user
        delivery.client = client_user
        delivery.save()
        
        assert permission.has_object_permission(request, None, delivery) is True
    
    def test_client_does_not_own_delivery(self, client_user):
        """Test that client who doesn't own delivery has no permission."""
        permission = IsClientOwner()
        
        # Create another client who owns the delivery
        other_client = User.objects.create_user(
            email="other@client.com",
            password="test123",
            role="client"
        )
        
        delivery = Delivery.objects.create(
            client=other_client,
            pickup_address="123 Pickup St",
            dropoff_address="456 Dropoff Ave",
            pickup_latitude=-26.2041,
            pickup_longitude=28.0473,
            package_description="Test delivery",
            status="SEARCHING"
        )
        
        request = MagicMock()
        request.user = client_user
        
        assert permission.has_object_permission(request, None, delivery) is False
    
    def test_admin_does_not_own_client_delivery(self, admin_user, delivery):
        """Test that admin is not treated as owner of client delivery."""
        permission = IsClientOwner()
        request = MagicMock()
        request.user = admin_user
        
        # This permission only checks ownership, not admin status
        assert permission.has_object_permission(request, None, delivery) is False
    
    def test_biker_does_not_own_delivery(self, biker_user, delivery):
        """Test that biker is not treated as owner."""
        permission = IsClientOwner()
        user, _ = biker_user  # Unpack tuple
        request = MagicMock()
        request.user = user
        
        assert permission.has_object_permission(request, None, delivery) is False


@pytest.mark.django_db
class TestIsAssignedBikerPermission:
    """Tests for the IsAssignedBiker permission class."""
    
    def test_assigned_biker_has_permission(self, biker_user, delivery_with_assignment):
        """Test that assigned biker has permission."""
        permission = IsAssignedBiker()
        user, _ = biker_user  # Unpack tuple: (user, biker)
        request = MagicMock()
        request.user = user
        
        # Ensure the assignment is for this biker
        delivery = delivery_with_assignment
        
        assert permission.has_object_permission(request, None, delivery) is True
    
    def test_unassigned_biker_has_no_permission(self, delivery_with_assignment):
        """Test that unassigned biker has no permission."""
        permission = IsAssignedBiker()
        
        # Create a different biker
        other_user = User.objects.create_user(
            email="other@biker.com",
            password="test123",
            role="biker"
        )
        Biker.objects.create(user=other_user, status="AVAILABLE")
        
        request = MagicMock()
        request.user = other_user
        
        assert permission.has_object_permission(request, None, delivery_with_assignment) is False
    
    def test_client_has_no_biker_permission(self, client_user, delivery_with_assignment):
        """Test that client user has no assigned biker permission."""
        permission = IsAssignedBiker()
        request = MagicMock()
        request.user = client_user
        
        # Client doesn't have biker_profile attribute
        assert permission.has_object_permission(request, None, delivery_with_assignment) is False
    
    def test_admin_has_no_biker_permission(self, admin_user, delivery_with_assignment):
        """Test that admin user has no assigned biker permission."""
        permission = IsAssignedBiker()
        request = MagicMock()
        request.user = admin_user
        
        # Admin doesn't have biker_profile attribute
        assert permission.has_object_permission(request, None, delivery_with_assignment) is False
    
    def test_user_without_biker_profile_returns_false(self, delivery_with_assignment):
        """Test that user without biker_profile returns False."""
        permission = IsAssignedBiker()
        
        # Create a user without biker profile
        user = User.objects.create_user(
            email="nobiker@test.com",
            password="test123",
            role="biker"  # Has role but no Biker object
        )
        
        request = MagicMock()
        request.user = user
        
        # Should return False because no biker_profile
        assert permission.has_object_permission(request, None, delivery_with_assignment) is False
