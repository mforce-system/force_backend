from .models import Biker, DeliveryAssignment, Delivery
from .utils import calculate_distance
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Maximum distance in kilometers to search for nearby bikers
SEARCH_RADIUS_KM = 5

# Minimum number of bikers to notify even if fewer are within radius
MIN_BIKERS_TO_NOTIFY = 3

def find_nearby_bikers(delivery):
    """
    Finds available bikers to notify about a new delivery.
    Strategy:
    - First finds all bikers within SEARCH_RADIUS_KM of the pickup location.
    - If fewer than MIN_BIKERS_TO_NOTIFY are found, expands to the closest bikers
      regardless of distance so at least MIN_BIKERS_TO_NOTIFY bikers are always notified.
    - Only considers bikers with status AVAILABLE and a known location.
    - Returns a list of biker objects sorted by distance (closest first).
    """
    # Only consider bikers who are available and have a recorded location
    bikers = Biker.objects.filter(
        status="AVAILABLE",
        current_latitude__isnull=False,
        current_longitude__isnull=False
    )

    # Calculate distance for every available biker
    bikers_with_distance = []
    for biker in bikers:
        distance = calculate_distance(
            delivery.pickup_latitude,
            delivery.pickup_longitude,
            biker.current_latitude,
            biker.current_longitude
        )
        bikers_with_distance.append((distance, biker))

    # Sort all bikers by distance — closest first
    bikers_with_distance.sort(key=lambda x: x[0])

    # Get bikers within the search radius
    nearby = [biker for distance, biker in bikers_with_distance
              if distance <= SEARCH_RADIUS_KM]

    # If we don't have enough bikers within radius, expand to closest available
    if len(nearby) < MIN_BIKERS_TO_NOTIFY:
        nearby = [biker for distance, biker in bikers_with_distance[:MIN_BIKERS_TO_NOTIFY]]

    return nearby


def accept_delivery(delivery_id, biker):
    """
    Allows a biker to accept a delivery.
    - Checks that the delivery exists and is still in SEARCHING status.
    - Ensures no other biker has already been assigned (prevents race conditions).
    - Creates a DeliveryAssignment and marks it as accepted.
    - Updates the delivery status to ASSIGNED.
    - Updates the biker's status to ON_DELIVERY.
    - Notifies all other nearby bikers that the delivery has been taken.
    - Returns the assignment if successful, or None if already taken.
    """
    try:
        delivery = Delivery.objects.get(id=delivery_id, status="SEARCHING")
    except Delivery.DoesNotExist:
        # Delivery not found or already assigned/completed
        return None

    # Check if an assignment already exists — another biker got there first
    if DeliveryAssignment.objects.filter(delivery=delivery).exists():
        return None

    # Create the assignment and mark it as accepted
    assignment = DeliveryAssignment.objects.create(
        delivery=delivery,
        biker=biker,
        accepted=True
    )

    # Update delivery status to ASSIGNED
    delivery.status = "ASSIGNED"
    delivery.save()

    # Mark the accepting biker as busy
    biker.status = "ON_DELIVERY"
    biker.save()

    # Notify all other nearby bikers that this delivery has been taken
    # so they can remove it from their available jobs list
    _notify_delivery_taken(delivery, accepted_by_biker=biker)

    return assignment


def _notify_delivery_taken(delivery, accepted_by_biker):
    """
    After a biker accepts a delivery, notify all other nearby bikers
    that the delivery is no longer available.
    - Finds all bikers near the pickup location.
    - Skips the biker who accepted it.
    - Sends a 'delivery_taken' message to all others via WebSocket.
    """
    nearby_bikers = find_nearby_bikers(delivery)
    channel_layer = get_channel_layer()

    for biker in nearby_bikers:
        # Don't notify the biker who just accepted it
        if biker.id == accepted_by_biker.id:
            continue

        # Send delivery_taken message so their UI can remove it
        async_to_sync(channel_layer.group_send)(
            f"biker_{biker.id}",
            {
                "type": "delivery_taken",
                "delivery_id": delivery.id,
                "message": "This delivery has been accepted by another biker"
            }
        )