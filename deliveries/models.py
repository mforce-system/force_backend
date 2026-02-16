from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


# -------------------------
# BIKER PROFILE
# -------------------------
class Biker(models.Model):
    STATUS_CHOICES = [
        ("AVAILABLE", "Available"),
        ("ON_DELIVERY", "On Delivery"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="biker_profile"
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="AVAILABLE"
    )

    def __str__(self):
        return f"Biker: {self.user.email} ({self.status})"


# -------------------------
# DELIVERY
# -------------------------
class Delivery(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ASSIGNED", "Assigned"),
        ("IN_TRANSIT", "In Transit"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    ]

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="deliveries"
    )

    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    package_description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Delivery {self.id} - {self.status}"


# -------------------------
# DELIVERY ASSIGNMENT
# -------------------------
class DeliveryAssignment(models.Model):
    delivery = models.OneToOneField(
        Delivery,
        on_delete=models.CASCADE,
        related_name="assignment"
    )

    biker = models.ForeignKey(
        Biker,
        on_delete=models.CASCADE,
        related_name="assignments"
    )

    accepted = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Assignment: Delivery {self.delivery.id} → {self.biker.user.email}"


# -------------------------
# DELIVERY LOCATION
# -------------------------
class DeliveryLocation(models.Model):
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="locations"
    )

    biker = models.ForeignKey(
        Biker,
        on_delete=models.CASCADE
    )

    latitude = models.FloatField()
    longitude = models.FloatField()

    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Location for Delivery {self.delivery.id}"


# -------------------------
# DELIVERY LOG (Lifecycle Logging)
# -------------------------
class DeliveryLog(models.Model):
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="logs"
    )

    message = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log: Delivery {self.delivery.id} - {self.message}"
