from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from ..models import DeliveryAssignment
from ..serializers import DeliveryAssignmentSerializer
from ..permissions import IsAdmin


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






