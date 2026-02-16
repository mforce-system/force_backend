from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    # Accounts & Auth
    path("api/", include("accounts.urls")),

    # Deliveries
    path("api/", include("deliveries.urls")),
]
