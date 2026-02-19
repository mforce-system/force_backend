from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch, Q

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
from .location import calculate_distance, estimate_eta


# =====================================
# DELIVERY VIEWSET
# =====================================
class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Delivery.objects.all()

        if hasattr(user, "biker_profile"):
            return Delivery.objects.filter(
                assignment__biker__user=user
            )

        return Delivery.objects.filter(client=user)

    def perform_create(self, serializer):
        # Auto-assign the current user as the client
        serializer.save(client=self.request.user, status="PENDING")

    @action(detail=False, methods=['get'])
    def my_deliveries(self, request):
        """Get current user's deliveries with stats"""
        deliveries = self.get_queryset()
        
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
        delivery = self.get_object()
        biker_id = request.data.get("biker_id")

        if not biker_id:
            return Response({"error": "biker_id is required"}, status=400)

        try:
            biker = Biker.objects.get(id=biker_id)
        except Biker.DoesNotExist:
            return Response({"error": "Biker not found"}, status=404)

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
def mark_delivered(self, request, pk=None):
    delivery = self.get_object()

    try:
        assignment = DeliveryAssignment.objects.select_related(
            "biker__user"
        ).get(delivery=delivery)
    except DeliveryAssignment.DoesNotExist:
        return Response({"error": "No assignment found"}, status=400)

    if assignment.biker.user != request.user:
        return Response({"error": "Unauthorized"}, status=403)

    delivery.status = "DELIVERED"
    delivery.save()

    assignment.biker.status = "AVAILABLE"
    assignment.biker.save()

    DeliveryLog.objects.create(
        delivery=delivery,
        message="Delivery completed"
    )

    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"delivery_{delivery.id}",
        {
            "type": "broadcast_completion"
        }
    )

    return Response({"message": "Delivery marked as DELIVERED"})


# =====================================
# ASSIGNMENT VIEWSET
# =====================================
class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAssignment.objects.all()
    serializer_class = DeliveryAssignmentSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


# =====================================
# LOCATION VIEWSET
# =====================================
class LocationViewSet(viewsets.ModelViewSet):
    serializer_class = DeliveryLocationSerializer
    permission_classes = [IsAuthenticated, IsAssignedBiker]

    def get_queryset(self):
        return DeliveryLocation.objects.filter(
            delivery__assignment__biker__user=self.request.user
        )
