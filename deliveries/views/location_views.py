from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from ..models import DeliveryLocation
from ..serializers import DeliveryLocationSerializer
from ..permissions import IsAssignedBiker


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