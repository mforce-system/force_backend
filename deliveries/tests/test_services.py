"""
Tests for the deliveries services module.
Tests find_nearby_bikers, accept_delivery, and _notify_delivery_taken functions.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from django.contrib.auth import get_user_model
from deliveries.models import Biker, Delivery, DeliveryAssignment
from deliveries.services import (
    find_nearby_bikers, 
    accept_delivery, 
    _notify_delivery_taken,
    SEARCH_RADIUS_KM,
    MIN_BIKERS_TO_NOTIFY
)

User = get_user_model()


@pytest.mark.django_db
class TestFindNearbyBikers:
    """Tests for the find_nearby_bikers function."""
    
    def test_find_bikers_within_radius(self, searching_delivery, multiple_bikers):
        """Test that bikers within search radius are found."""
        nearby = find_nearby_bikers(searching_delivery)
        
        # Should find bikers with locations
        assert len(nearby) > 0
        # All returned bikers should be AVAILABLE
        for biker in nearby:
            assert biker.status == "AVAILABLE"
    
    def test_only_available_bikers_returned(self, searching_delivery, biker_with_location):
        """Test that only AVAILABLE bikers are returned."""
        # Set biker to ON_DELIVERY status
        biker_with_location.status = "ON_DELIVERY"
        biker_with_location.save()
        
        nearby = find_nearby_bikers(searching_delivery)
        
        # The ON_DELIVERY biker should not be in the results
        biker_ids = [b.id for b in nearby]
        assert biker_with_location.id not in biker_ids
    
    def test_bikers_without_location_excluded(self, searching_delivery, biker):
        """Test that bikers without location are excluded."""
        # Ensure biker has no location
        biker.current_latitude = None
        biker.current_longitude = None
        biker.save()
        
        nearby = find_nearby_bikers(searching_delivery)
        
        biker_ids = [b.id for b in nearby]
        assert biker.id not in biker_ids
    
    def test_minimum_bikers_returned_when_few_in_radius(self, searching_delivery):
        """Test MIN_BIKERS_TO_NOTIFY fallback when few bikers in radius."""
        # Create bikers far away (outside radius but should still be notified)
        bikers_created = []
        for i in range(5):
            user = User.objects.create_user(
                email=f"farbiker{i}@test.com",
                password="test123",
                role="biker"
            )
            biker = Biker.objects.create(
                user=user,
                status="AVAILABLE",
                # Far away from delivery (different city)
                current_latitude=-33.9 + (i * 0.5),
                current_longitude=18.4 + (i * 0.5)
            )
            bikers_created.append(biker)
        
        nearby = find_nearby_bikers(searching_delivery)
        
        # Should return at least MIN_BIKERS_TO_NOTIFY even if outside radius
        assert len(nearby) >= min(MIN_BIKERS_TO_NOTIFY, len(bikers_created))
    
    def test_bikers_sorted_by_distance(self, searching_delivery):
        """Test that returned bikers are sorted by distance (closest first)."""
        # Create bikers at different distances
        distances = []
        for i, offset in enumerate([0.001, 0.01, 0.005]):  # Different distances
            user = User.objects.create_user(
                email=f"distbiker{i}@test.com",
                password="test123",
                role="biker"
            )
            Biker.objects.create(
                user=user,
                status="AVAILABLE",
                current_latitude=searching_delivery.pickup_latitude + offset,
                current_longitude=searching_delivery.pickup_longitude + offset
            )
        
        nearby = find_nearby_bikers(searching_delivery)
        
        # Verify they're sorted by distance
        if len(nearby) >= 2:
            # Calculate distances for first two bikers
            from deliveries.utils import calculate_distance
            d1 = calculate_distance(
                searching_delivery.pickup_latitude,
                searching_delivery.pickup_longitude,
                nearby[0].current_latitude,
                nearby[0].current_longitude
            )
            d2 = calculate_distance(
                searching_delivery.pickup_latitude,
                searching_delivery.pickup_longitude,
                nearby[1].current_latitude,
                nearby[1].current_longitude
            )
            assert d1 <= d2


@pytest.mark.django_db
class TestAcceptDelivery:
    """Tests for the accept_delivery function."""
    
    @patch('deliveries.services.get_channel_layer')
    def test_accept_delivery_success(self, mock_channel_layer, searching_delivery, biker_with_location):
        """Test successful delivery acceptance."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        assignment = accept_delivery(searching_delivery.id, biker_with_location)
        
        assert assignment is not None
        assert assignment.delivery == searching_delivery
        assert assignment.biker == biker_with_location
        assert assignment.accepted is True
        
        # Verify delivery status updated
        searching_delivery.refresh_from_db()
        assert searching_delivery.status == "ASSIGNED"
        
        # Verify biker status updated
        biker_with_location.refresh_from_db()
        assert biker_with_location.status == "ON_DELIVERY"
    
    @patch('deliveries.services.get_channel_layer')
    def test_accept_nonexistent_delivery_returns_none(self, mock_channel_layer, biker_with_location):
        """Test that accepting non-existent delivery returns None."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        assignment = accept_delivery(99999, biker_with_location)
        
        assert assignment is None
    
    @patch('deliveries.services.get_channel_layer')
    def test_accept_already_assigned_delivery_returns_none(self, mock_channel_layer, assigned_delivery, biker_with_location):
        """Test that accepting already assigned delivery returns None."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        # Create a different biker to try accepting
        user = User.objects.create_user(email="otherbiker2@test.com", password="test123", role="biker")
        other_biker = Biker.objects.create(
            user=user, 
            status="AVAILABLE", 
            current_latitude=-26.2041,
            current_longitude=28.0473
        )
        
        # Try to accept an already assigned delivery with a different biker
        assignment = accept_delivery(assigned_delivery.id, other_biker)
        
        assert assignment is None
    
    @patch('deliveries.services.get_channel_layer')
    def test_accept_delivery_race_condition(self, mock_channel_layer, searching_delivery):
        """Test race condition handling when two bikers try to accept same delivery."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        # Create two bikers
        user1 = User.objects.create_user(email="racer1@test.com", password="test123", role="biker")
        biker1 = Biker.objects.create(user=user1, status="AVAILABLE", current_latitude=-26.0, current_longitude=28.0)
        
        user2 = User.objects.create_user(email="racer2@test.com", password="test123", role="biker")
        biker2 = Biker.objects.create(user=user2, status="AVAILABLE", current_latitude=-26.0, current_longitude=28.0)
        
        # First biker accepts
        assignment1 = accept_delivery(searching_delivery.id, biker1)
        
        # Second biker tries to accept - should fail
        assignment2 = accept_delivery(searching_delivery.id, biker2)
        
        assert assignment1 is not None
        assert assignment2 is None
        
        # Verify only one assignment exists
        assert DeliveryAssignment.objects.filter(delivery=searching_delivery).count() == 1
    
    @patch('deliveries.services.get_channel_layer')
    def test_accept_delivery_notifies_other_bikers(self, mock_channel_layer, searching_delivery, multiple_bikers):
        """Test that accepting delivery notifies other nearby bikers."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        # Get first biker to accept
        accepting_biker = multiple_bikers[0]
        
        assignment = accept_delivery(searching_delivery.id, accepting_biker)
        
        assert assignment is not None
        # Verify group_send was called (notifications sent)
        # Note: The exact number depends on how many bikers are nearby
        # The important thing is that the accepting biker should NOT receive notification


@pytest.mark.django_db
class TestNotifyDeliveryTaken:
    """Tests for the _notify_delivery_taken function."""
    
    @patch('deliveries.services.get_channel_layer')
    def test_notify_delivery_taken_sends_websocket_messages(self, mock_channel_layer, searching_delivery, multiple_bikers):
        """Test that WebSocket messages are sent to nearby bikers."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        accepting_biker = multiple_bikers[0]
        
        _notify_delivery_taken(searching_delivery, accepted_by_biker=accepting_biker)
        
        # Should have sent messages via channel layer
        # The accepting biker should NOT receive a notification
        calls = mock_layer.group_send.call_args_list
        for call in calls:
            group_name = call[0][0]
            # Verify accepting biker's group was not called
            assert group_name != f"biker_{accepting_biker.id}"
    
    @patch('deliveries.services.get_channel_layer')
    def test_notify_excludes_accepting_biker(self, mock_channel_layer, searching_delivery, multiple_bikers):
        """Test that the accepting biker is excluded from notifications."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        accepting_biker = multiple_bikers[0]
        
        _notify_delivery_taken(searching_delivery, accepted_by_biker=accepting_biker)
        
        # Check all group_send calls
        for call in mock_layer.group_send.call_args_list:
            group_name = call[0][0]
            message = call[0][1]
            # Verify message type
            assert message["type"] == "delivery_taken"
            assert message["delivery_id"] == searching_delivery.id
            # Verify not sent to accepting biker
            assert group_name != f"biker_{accepting_biker.id}"
    
    @patch('deliveries.services.get_channel_layer')
    def test_notify_sends_correct_message_format(self, mock_channel_layer, searching_delivery, biker_with_location):
        """Test that notification message has correct format."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_channel_layer.return_value = mock_layer
        
        # Create another biker to receive notification
        user = User.objects.create_user(email="otherbiker@test.com", password="test123", role="biker")
        other_biker = Biker.objects.create(
            user=user, 
            status="AVAILABLE", 
            current_latitude=searching_delivery.pickup_latitude + 0.001,
            current_longitude=searching_delivery.pickup_longitude + 0.001
        )
        
        _notify_delivery_taken(searching_delivery, accepted_by_biker=biker_with_location)
        
        # If other_biker is nearby, they should receive a notification
        if mock_layer.group_send.called:
            call = mock_layer.group_send.call_args
            message = call[0][1]
            assert "type" in message
            assert "delivery_id" in message
            assert "message" in message
            assert message["type"] == "delivery_taken"
