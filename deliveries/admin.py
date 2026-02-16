from django.contrib import admin
from .models import (
    Biker,
    Delivery,
    DeliveryAssignment,
    DeliveryLog,
    DeliveryLocation
)

admin.site.register(Biker)
admin.site.register(Delivery)
admin.site.register(DeliveryAssignment)
admin.site.register(DeliveryLog)
admin.site.register(DeliveryLocation)
