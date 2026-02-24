from .models import Biker, DeliveryAssignment, Delivery
from .utils import calculate_distance

# Maximum distance in kilometers to search for nearby bikers
SEARCH_RADIUS_KM = 5  # you can adjust


def find_nearby_bikers(delivery):
    """
    Finds all available bikers within SEARCH_RADIUS_KM of the delivery pickup location.
    - Filters only bikers with status AVAILABLE and a known location.
    - Uses the haversine formula (via calculate_distance) to check proximity.
    - Returns a list of biker objects within range.
    """
    # Only consider bikers who are available and have a recorded location
    bikers = Biker.objects.filter(
        status="AVAILABLE",
        current_latitude__isnull=False,
        current_longitude__isnull=False
    )

    nearby = []

    for biker in bikers:
        # Calculate distance between pickup point and biker's current location
        distance = calculate_distance(
            delivery.pickup_latitude,
            delivery.pickup_longitude,
            biker.current_latitude,
            biker.current_longitude
        )

        # Only include bikers within the search radius
        if distance <= SEARCH_RADIUS_KM:
            nearby.append(biker)

    return nearby


def accept_delivery(delivery_id, biker):
    """
    Allows a biker to accept a delivery.
    - Checks that the delivery exists and is still in SEARCHING status.
    - Ensures no other biker has already been assigned.
    - Creates a DeliveryAssignment and marks it as accepted.
    - Updates the delivery status to ASSIGNED.
    - Updates the biker's status to ON_DELIVERY.
    - Returns the assignment if successful, or None if already taken.
    """
    try:
        delivery = Delivery.objects.get(id=delivery_id, status="SEARCHING")
    except Delivery.DoesNotExist:
        # Delivery not found or already assigned/completed
        return None

    # Check if an assignment already exists for this delivery
    if DeliveryAssignment.objects.filter(delivery=delivery).exists():
        return None  # Another biker already accepted it

    # Create the assignment and mark it as accepted
    assignment = DeliveryAssignment.objects.create(
        delivery=delivery,
        biker=biker,
        accepted=True
    )

    # Update delivery status to ASSIGNED
    delivery.status = "ASSIGNED"
    delivery.save()

    # Mark the biker as on a delivery so they stop receiving new requests
    biker.status = "ON_DELIVERY"
    biker.save()

    return assignment