from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from ..services import find_nearby_bikers, accept_delivery

from ..models import (
    Delivery,
    DeliveryAssignment,
    Biker,
    DeliveryLog
)
from ..serializers import DeliverySerializer
from ..permissions import IsAdmin


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
        - Bikers see deliveries assigned to them AND deliveries in SEARCHING status.
        - Regular clients see only their own deliveries.
        """
        user = self.request.user

        # Admins can see everything
        if user.is_staff:
            return Delivery.objects.all()

        # Bikers see SEARCHING deliveries and their own assigned deliveries
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
        Returns the current user's deliveries along with summary stats.
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
        """
        delivery = self.get_object()
        biker_id = request.data.get("biker_id")

        if not biker_id:
            return Response({"error": "biker_id is required"}, status=400)

        try:
            biker = Biker.objects.get(id=biker_id)
        except Biker.DoesNotExist:
            return Response({"error": "Biker not found"}, status=404)

        # Create or update the assignment (only one biker per delivery at a time)
        assignment, created = DeliveryAssignment.objects.update_or_create(
            delivery=delivery,
            defaults={"biker": biker}
        )

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
        """
        delivery = self.get_object()

        # Get the biker profile linked to the currently logged-in user
        biker = request.user.biker_profile

        # Attempt to accept the delivery — returns None if already assigned
        assignment = accept_delivery(delivery.id, biker)

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
        """
        delivery = self.get_object()

        try:
            assignment = DeliveryAssignment.objects.select_related(
                "biker__user"
            ).get(delivery=delivery)
        except DeliveryAssignment.DoesNotExist:
            return Response({"error": "No assignment found"}, status=400)

        # Only the assigned biker can mark the delivery as delivered
        if assignment.biker.user != request.user:
            return Response({"error": "Unauthorized"}, status=403)

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
                "type": "broadcast_completion"
            }
        )

        return Response({"message": "Delivery marked as DELIVERED"})