from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from django.db.models import Prefetch, Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .services import find_nearby_bikers, accept_delivery

from .models import (
    Delivery,
    DeliveryAssignment,
    DeliveryLocation,
    Biker,
    DeliveryLog
)
from .serializers import (
    DeliverySerializer,
    DeliveryAssignmentSerializer,
    DeliveryLocationSerializer,
)
from .permissions import IsAdmin, IsAssignedBiker


# =====================================
# DELIVERY VIEWSET
# =====================================
class DeliveryViewSet(viewsets.ModelViewSet):
    """
    Handles all CRUD operations for Deliveries.
    - Clients can create and view their own deliveries.
    - Bikers can view deliveries assigned to them.
    - Admins can view and manage all deliveries.
    """
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        """
        Called when a client creates a new delivery.
        - Saves the delivery with the current user as the client and sets status to SEARCHING.
        - Finds nearby available bikers using the haversine distance calculation.
        - Notifies each nearby biker via WebSocket (Django Channels) with the delivery details.
        """
        # Save delivery, auto-assigning the logged-in user as the client
        delivery = serializer.save(client=self.request.user, status="SEARCHING")

        # Find bikers within the search radius of the pickup location
        nearby_bikers = find_nearby_bikers(delivery)

        # Get the channel layer for WebSocket communication
        channel_layer = get_channel_layer()

        # Send a real-time delivery request notification to each nearby biker
        for biker in nearby_bikers:
            async_to_sync(channel_layer.group_send)(
                f"biker_{biker.id}",  # Each biker listens on their own group channel
                {
                    "type": "delivery_request",  # Maps to a consumer handler method
                    "delivery_id": delivery.id,
                    "pickup_address": delivery.pickup_address,
                    "dropoff_address": delivery.dropoff_address,
                }
            )

    def get_queryset(self):
        """
        Returns a filtered queryset based on who is making the request:
        - Admins (is_staff) see all deliveries.
        - Bikers see deliveries assigned to them AND deliveries in SEARCHING status
          (so they can find and accept available deliveries nearby).
        - Regular clients see only their own deliveries.
        """
        user = self.request.user

        # Admins can see everything
        if user.is_staff:
            return Delivery.objects.all()

        # Bikers see:
        # 1. Deliveries currently in SEARCHING status (available to accept)
        # 2. Deliveries already assigned to them
        if hasattr(user, "biker_profile"):
            return Delivery.objects.filter(
                models.Q(status="SEARCHING") |
                models.Q(assignment__biker__user=user)
            ).distinct()

        # Clients see only their own deliveries
        return Delivery.objects.filter(client=user)

    @action(detail=False, methods=['get'])
    def my_deliveries(self, request):
        """
        Custom endpoint: GET /deliveries/my_deliveries/
        Returns the current user's deliveries along with summary stats
        (total, pending, in transit, delivered).
        """
        deliveries = self.get_queryset()

        # Build a summary of delivery counts by status
        stats = {
            'total': deliveries.count(),
            'pending': deliveries.filter(status='PENDING').count(),
            'in_transit': deliveries.filter(status='IN_TRANSIT').count(),
            'delivered': deliveries.filter(status='DELIVERED').count(),
        }

        serializer = self.get_serializer(deliveries, many=True)
        return Response({
            'stats': stats,
            'deliveries': serializer.data
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def assign(self, request, pk=None):
        """
        Custom endpoint: POST /deliveries/{id}/assign/
        Admin-only action to manually assign a biker to a delivery.
        - Requires biker_id in the request body.
        - Creates or updates the DeliveryAssignment record.
        - Updates the delivery status to ASSIGNED.
        """
        delivery = self.get_object()
        biker_id = request.data.get("biker_id")

        # Validate that biker_id was provided
        if not biker_id:
            return Response({"error": "biker_id is required"}, status=400)

        # Check that the biker exists
        try:
            biker = Biker.objects.get(id=biker_id)
        except Biker.DoesNotExist:
            return Response({"error": "Biker not found"}, status=404)

        # Create or update the assignment (only one biker per delivery at a time)
        assignment, created = DeliveryAssignment.objects.update_or_create(
            delivery=delivery,
            defaults={"biker": biker}
        )

        # Mark the delivery as assigned
        delivery.status = "ASSIGNED"
        delivery.save()

        return Response({
            "message": "Biker assigned successfully",
            "assignment_id": assignment.id,
        })

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def accept(self, request, pk=None):
        """
        Custom endpoint: POST /deliveries/{id}/accept/
        Allows a biker to accept a delivery that was sent to them.
        - Retrieves the biker profile from the logged-in user.
        - Calls accept_delivery service which handles the assignment logic.
        - Returns an error if the delivery was already accepted by another biker.
        """
        delivery = self.get_object()

        # Get the biker profile linked to the currently logged-in user
        biker = request.user.biker_profile

        # Attempt to accept the delivery — returns None if already assigned
        assignment = accept_delivery(delivery.id, biker)

        # If no assignment was returned, another biker already claimed it
        if not assignment:
            return Response(
                {"error": "Delivery already assigned"},
                status=400
            )

        return Response({"message": "Delivery accepted"})

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def mark_delivered(self, request, pk=None):
        """
        Custom endpoint: POST /deliveries/{id}/mark_delivered/
        Allows the assigned biker to mark a delivery as completed.
        - Verifies the requesting user is the assigned biker.
        - Updates delivery status to DELIVERED.
        - Sets the biker's status back to AVAILABLE.
        - Logs the completion event.
        - Notifies the delivery group channel via WebSocket.
        """
        delivery = self.get_object()

        # Fetch the assignment and related biker/user in one query
        try:
            assignment = DeliveryAssignment.objects.select_related(
                "biker__user"
            ).get(delivery=delivery)
        except DeliveryAssignment.DoesNotExist:
            return Response({"error": "No assignment found"}, status=400)

        # Only the assigned biker can mark the delivery as delivered
        if assignment.biker.user != request.user:
            return Response({"error": "Unauthorized"}, status=403)

        # Update delivery status to DELIVERED
        delivery.status = "DELIVERED"
        delivery.save()

        # Free up the biker to take new deliveries
        assignment.biker.status = "AVAILABLE"
        assignment.biker.save()

        # Create a log entry for the completion event
        DeliveryLog.objects.create(
            delivery=delivery,
            message="Delivery completed"
        )

        # Notify all listeners on this delivery's WebSocket group
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"delivery_{delivery.id}",
            {
                "type": "broadcast_completion"  # Maps to a consumer handler method
            }
        )

        return Response({"message": "Delivery marked as DELIVERED"})


# =====================================
# ASSIGNMENT VIEWSET
# =====================================
class AssignmentViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD operations for DeliveryAssignments.
    Restricted to admin users only.
    """
    queryset = DeliveryAssignment.objects.all()
    serializer_class = DeliveryAssignmentSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


# =====================================
# LOCATION VIEWSET
# =====================================
class LocationViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD operations for DeliveryLocations (real-time location tracking).
    Only the biker assigned to the delivery can access or update location data.
    """
    serializer_class = DeliveryLocationSerializer
    permission_classes = [IsAuthenticated, IsAssignedBiker]

    def get_queryset(self):
        """
        Returns only the location records for deliveries
        assigned to the currently logged-in biker.
        """
        return DeliveryLocation.objects.filter(
            delivery__assignment__biker__user=self.request.user
        )