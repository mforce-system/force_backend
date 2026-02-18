from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .health import HealthCheckView

urlpatterns = [
    # Health check
    path("health/", HealthCheckView.as_view(), name="health_check"),
    
    path("admin/", admin.site.urls),

    # JWT Authentication
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # Accounts & Auth
    path("api/", include("accounts.urls")),

    # Deliveries
    path("api/", include("deliveries.urls")),
]
