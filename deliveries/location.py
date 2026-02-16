from django.db import models
from django.utils import timezone

class DeliveryLocation(models.Model):
    delivery = models.ForeignKey(
        "deliveries.Delivery",
        on_delete=models.CASCADE,
        related_name="locations"
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "delivery_locations"
        ordering = ["-recorded_at"]
