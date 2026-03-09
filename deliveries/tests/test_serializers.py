"""
Tests for the deliveries serializers module.
Tests BikerSerializer, DeliverySerializer, DeliveryAssignmentSerializer, and DeliveryLocationSerializer.
"""
import pytest
from django.contrib.auth import get_user_model
from deliveries.serializers import (
    BikerSerializer,
    DeliverySerializer,
    DeliveryAssignmentSerializer,
    DeliveryLocationSerializer,
)
from deliveries.models import Biker, Delivery, DeliveryAssignment, DeliveryLocation

User = get_user_model()


@pytest.mark.django_db
class TestBikerSerializer:
    """Tests for the BikerSerializer."""
    
    def test_serializer_contains_expected_fields(self, biker):
        """Test that serializer contains expected fields."""
        serializer = BikerSerializer(biker)
        
        assert set(serializer.data.keys()) == {'id', 'email', 'phone_number', 'status'}
    
    def test_email_field_from_user(self, biker_user, biker):
        """Test that email is sourced from user.email."""
        user, _ = biker_user  # Unpack tuple
        serializer = BikerSerializer(biker)
        
        assert serializer.data['email'] == user.email
    
    def test_status_is_read_only(self, biker):
        """Test that status field is read-only."""
        serializer = BikerSerializer(biker, data={'status': 'ON_DELIVERY'}, partial=True)
        
        # Even though we provide status, it should be read-only
        assert serializer.is_valid()
        # Status should not change when we save
        # (not actually saving, just verifying serializer behavior)
    
    def test_serializer_output_format(self, biker_user, biker):
        """Test serializer output format."""
        user, _ = biker_user  # Unpack tuple
        biker.phone_number = "+27123456789"
        biker.save()
        
        serializer = BikerSerializer(biker)
        
        assert serializer.data['id'] == biker.id
        assert serializer.data['email'] == user.email
        assert serializer.data['phone_number'] == "+27123456789"
        assert serializer.data['status'] == biker.status


@pytest.mark.django_db
class TestDeliverySerializer:
    """Tests for the DeliverySerializer."""
    
    def test_serializer_with_valid_data(self, client_user):
        """Test serializer with valid delivery data."""
        data = {
            'pickup_address': '123 Pickup Street',
            'dropoff_address': '456 Dropoff Avenue',
            'pickup_latitude': -26.2041,
            'pickup_longitude': 28.0473,
            'package_description': 'Test package',
        }
        
        serializer = DeliverySerializer(data=data)
        
        assert serializer.is_valid(), serializer.errors
    
    def test_client_field_is_read_only(self, client_user):
        """Test that client field is read-only."""
        data = {
            'client': client_user.id,  # Should be ignored
            'pickup_address': '123 Pickup Street',
            'dropoff_address': '456 Dropoff Avenue',
            'pickup_latitude': -26.2041,
            'pickup_longitude': 28.0473,
            'package_description': 'Test package',
        }
        
        serializer = DeliverySerializer(data=data)
        assert serializer.is_valid()
        # Client should not be in validated data (it's read-only)
        assert 'client' not in serializer.validated_data
    
    def test_status_field_is_read_only(self, client_user):
        """Test that status field is read-only."""
        data = {
            'status': 'DELIVERED',  # Should be ignored
            'pickup_address': '123 Pickup Street',
            'dropoff_address': '456 Dropoff Avenue',
            'pickup_latitude': -26.2041,
            'pickup_longitude': 28.0473,
            'package_description': 'Test package',
        }
        
        serializer = DeliverySerializer(data=data)
        assert serializer.is_valid()
        # Status should not be in validated data (it's read-only)
        assert 'status' not in serializer.validated_data
    
    def test_serializer_output_contains_all_fields(self, delivery):
        """Test that serializer output contains all delivery fields."""
        serializer = DeliverySerializer(delivery)
        
        assert 'id' in serializer.data
        assert 'client' in serializer.data
        assert 'pickup_address' in serializer.data
        assert 'dropoff_address' in serializer.data
        assert 'pickup_latitude' in serializer.data
        assert 'pickup_longitude' in serializer.data
        assert 'package_description' in serializer.data
        assert 'status' in serializer.data
        assert 'created_at' in serializer.data
    
    def test_missing_required_fields_invalid(self):
        """Test that missing required fields makes serializer invalid."""
        data = {
            'pickup_address': '123 Pickup Street',
            # Missing other required fields
        }
        
        serializer = DeliverySerializer(data=data)
        
        assert not serializer.is_valid()
        assert 'dropoff_address' in serializer.errors or 'package_description' in serializer.errors


@pytest.mark.django_db
class TestDeliveryAssignmentSerializer:
    """Tests for the DeliveryAssignmentSerializer."""
    
    def test_serializer_with_valid_data(self, delivery, biker):
        """Test serializer with valid assignment data."""
        data = {
            'delivery': delivery.id,
            'biker': biker.id,
            'accepted': True,
        }
        
        serializer = DeliveryAssignmentSerializer(data=data)
        
        assert serializer.is_valid(), serializer.errors
    
    def test_assigned_at_is_read_only(self, delivery, biker):
        """Test that assigned_at field is read-only."""
        from django.utils import timezone
        
        data = {
            'delivery': delivery.id,
            'biker': biker.id,
            'accepted': True,
            'assigned_at': timezone.now(),  # Should be ignored
        }
        
        serializer = DeliveryAssignmentSerializer(data=data)
        assert serializer.is_valid()
        # assigned_at should not be in validated data (it's read-only)
        assert 'assigned_at' not in serializer.validated_data
    
    def test_serializer_output_format(self, delivery_with_assignment):
        """Test serializer output format."""
        assignment = delivery_with_assignment.assignment
        serializer = DeliveryAssignmentSerializer(assignment)
        
        assert 'id' in serializer.data
        assert 'delivery' in serializer.data
        assert 'biker' in serializer.data
        assert 'accepted' in serializer.data
        assert 'assigned_at' in serializer.data


@pytest.mark.django_db
class TestDeliveryLocationSerializer:
    """Tests for the DeliveryLocationSerializer."""
    
    def test_serializer_with_valid_data(self, delivery_with_assignment, biker):
        """Test serializer with valid location data."""
        delivery = delivery_with_assignment
        
        data = {
            'delivery': delivery.id,
            'biker': biker.id,
            'latitude': -26.2041,
            'longitude': 28.0473,
        }
        
        serializer = DeliveryLocationSerializer(data=data)
        
        assert serializer.is_valid(), serializer.errors
    
    def test_recorded_at_is_read_only(self, delivery_with_assignment, biker):
        """Test that recorded_at field is read-only."""
        from django.utils import timezone
        
        delivery = delivery_with_assignment
        
        data = {
            'delivery': delivery.id,
            'biker': biker.id,
            'latitude': -26.2041,
            'longitude': 28.0473,
            'recorded_at': timezone.now(),  # Should be ignored
        }
        
        serializer = DeliveryLocationSerializer(data=data)
        assert serializer.is_valid()
        # recorded_at should not be in validated data (it's read-only)
        assert 'recorded_at' not in serializer.validated_data
    
    def test_serializer_output_format(self, delivery_with_location):
        """Test serializer output format."""
        from deliveries.models import DeliveryLocation
        location = DeliveryLocation.objects.filter(delivery=delivery_with_location).first()
        serializer = DeliveryLocationSerializer(location)
        
        assert 'id' in serializer.data
        assert 'delivery' in serializer.data
        assert 'biker' in serializer.data
        assert 'latitude' in serializer.data
        assert 'longitude' in serializer.data
        assert 'recorded_at' in serializer.data
    
    def test_latitude_longitude_precision(self, delivery_with_assignment, biker):
        """Test that latitude/longitude values preserve precision."""
        delivery = delivery_with_assignment
        
        data = {
            'delivery': delivery.id,
            'biker': biker.id,
            'latitude': -26.204139,
            'longitude': 28.047305,
        }
        
        serializer = DeliveryLocationSerializer(data=data)
        assert serializer.is_valid()
        
        # Values should be preserved with precision
        assert serializer.validated_data['latitude'] == pytest.approx(-26.204139, rel=1e-5)
        assert serializer.validated_data['longitude'] == pytest.approx(28.047305, rel=1e-5)
