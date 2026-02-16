from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeliveryViewSet, AssignmentViewSet, LocationViewSet

router = DefaultRouter()
router.register("deliveries", DeliveryViewSet, basename="deliveries")
router.register("assignments", AssignmentViewSet, basename="assignments")
router.register("locations", LocationViewSet, basename="locations")

urlpatterns = [
    path("", include(router.urls)),
]
