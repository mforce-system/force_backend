
# This file makes the views directory a Python package
# and exposes all viewsets for easy importing in urls.py

from .delivery_views import DeliveryViewSet
from .assignment_views import AssignmentViewSet
from .location_views import LocationViewSet

__all__ = ["DeliveryViewSet", "AssignmentViewSet", "LocationViewSet"]
















