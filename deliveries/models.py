from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


# -------------------------
# BIKER PROFILE
# -------------------------
class Biker(models.Model):
    """
    Represents a delivery biker linked to a user account.
    - Tracks the biker's current status and real-time location.
    - current_latitude and current_longitude are updated as the biker moves.
    """
    STATUS_CHOICES = [
        ("AVAILABLE", "Available"),       # Biker is free and can accept deliveries
        ("ON_DELIVERY", "On Delivery"),   # Biker is currently handling a delivery
    ]

    # One biker profile per user account
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

    # Real-time location fields — updated as the biker moves
    current_latitude = models.FloatField(null=True, blank=True)
    current_longitude = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Biker: {self.user.email} ({self.status})"


# -------------------------
# DELIVERY
# -------------------------
class Delivery(models.Model):
    """
    Represents a delivery request made by a client.
    - Tracks the pickup and dropoff addresses and coordinates.
    - Status progresses: PENDING → SEARCHING → ASSIGNED → IN_TRANSIT → DELIVERED.
    """
    STATUS_CHOICES = [
        ("PENDING", "Pending"),         # Just created, not yet searching for a biker
        ("SEARCHING", "Searching"),     # Actively looking for a nearby biker
        ("ASSIGNED", "Assigned"),       # A biker has been assigned
        ("IN_TRANSIT", "In Transit"),   # Biker has picked up and is on the way
        ("DELIVERED", "Delivered"),     # Delivery completed
    ]

    # The client who requested the delivery
    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="deliveries"
    )

    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    package_description = models.TextField()

    # Coordinates for the pickup location — used to find nearby bikers
    pickup_latitude = models.FloatField(null=True, blank=True)
    pickup_longitude = models.FloatField(null=True, blank=True)

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
    """
    Links a Delivery to a Biker.
    - One delivery can only have one assignment at a time (OneToOne).
    - 'accepted' flag is set to True when the biker confirms the job.
    """

    # Each delivery can only be assigned to one biker at a time
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

    # True once the biker has explicitly accepted the delivery
    accepted = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Assignment: Delivery {self.delivery.id} → {self.biker.user.email}"


# -------------------------
# DELIVERY LOCATION
# -------------------------
class DeliveryLocation(models.Model):
    """
    Stores a history of location updates sent by the biker during a delivery.
    - Each record is a snapshot of the biker's position at a point in time.
    - Used for real-time tracking and route history.
    """

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="locations"
    )

    biker = models.ForeignKey(
        Biker,
        on_delete=models.CASCADE
    )

    # The biker's coordinates at the time of this update
    latitude = models.FloatField()
    longitude = models.FloatField()

    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Location for Delivery {self.delivery.id}"


# -------------------------
# DELIVERY LOG
# -------------------------
class DeliveryLog(models.Model):
    """
    Records key lifecycle events for a delivery.
    - Each log entry captures a message and timestamp.
    - Used for auditing and debugging delivery progress.
    """

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="logs"
    )

    # Human-readable description of the event (e.g. "Delivery started (IN_TRANSIT)")
    message = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log: Delivery {self.delivery.id} - {self.message}"