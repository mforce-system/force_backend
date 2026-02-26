import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from .models import (
    Delivery,
    DeliveryAssignment,
    Biker,
    DeliveryLocation,
    DeliveryLog
)


# =====================================
# TRACKING CONSUMER
# Used by: clients and admins to watch a delivery in real time
# URL: ws://tracking/<delivery_id>/
# =====================================
class TrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that handles real-time delivery tracking.
    - Clients can watch the delivery location in real time.
    - Bikers send location updates which are broadcast to the group.
    - Admins can observe any delivery.
    """

    async def connect(self):
        """
        Called when a WebSocket connection is initiated.
        - Rejects anonymous users.
        - Loads the delivery from the URL parameter.
        - Determines the user's role (admin, biker, or client).
        - For bikers, verifies they are the assigned biker and have accepted the delivery.
        - Adds the biker to their personal channel group so they can receive delivery requests.
        - Adds the connection to the delivery group and confirms the connection.
        """
        user = self.scope["user"]

        # Reject unauthenticated connections immediately
        if not user or user.is_anonymous:
            await self.close(code=4001)
            return

        # Extract delivery_id from the WebSocket URL (e.g. ws/tracking/<delivery_id>/)
        self.delivery_id = self.scope["url_route"]["kwargs"]["delivery_id"]
        self.group_name = f"delivery_{self.delivery_id}"

        # Load the delivery from the database
        self.delivery = await self.get_delivery(self.delivery_id)
        if not self.delivery:
            await self.close(code=4004)  # Delivery not found
            return

        # Determine what role this user has (admin, biker, or client)
        self.role = await self.get_user_role(user)

        if self.role == "biker":
            # Bikers must have an accepted assignment to connect
            assignment = await self.get_assignment(self.delivery_id)

            if not assignment or not assignment.accepted:
                await self.close(code=4003)  # No valid assignment
                return

            # Ensure the biker connecting is the one actually assigned
            if assignment.biker.user.id != user.id:
                await self.close(code=4003)  # Wrong biker
                return

            self.biker = assignment.biker

            # Also add biker to their personal group so they receive delivery request notifications
            await self.channel_layer.group_add(
                f"biker_{self.biker.id}",
                self.channel_name
            )

        # Add this connection to the shared delivery tracking group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Accept the WebSocket connection
        await self.accept()

        # Notify the client that the connection was successful
        await self.send(json.dumps({
            "type": "connection_established",
            "delivery_id": self.delivery_id,
            "role": self.role
        }))

    async def disconnect(self, close_code):
        """
        Called when the WebSocket connection is closed.
        Removes this connection from the delivery group to stop receiving broadcasts.
        """
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Called when the client sends a message over the WebSocket.
        - Only bikers can send location updates.
        - Saves the location to the database.
        - Auto-starts the delivery if it is still in ASSIGNED status.
        - Broadcasts the new location to everyone in the delivery group.
        """
        data = json.loads(text_data)

        if self.role == "biker" and data.get("type") == "location_update":
            latitude = data.get("latitude")
            longitude = data.get("longitude")

            # Persist the location update to the database
            await self.save_location(latitude, longitude)

            # If delivery hasn't started yet, automatically move it to IN_TRANSIT
            await self.auto_start_delivery()

            # Broadcast the new location to all group members (client, admin, etc.)
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "broadcast_location",
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )

    async def broadcast_location(self, event):
        """
        Handler for 'broadcast_location' group messages.
        Sends the biker's updated coordinates to this WebSocket connection.
        """
        await self.send(json.dumps({
            "type": "location_update",
            "latitude": event["latitude"],
            "longitude": event["longitude"],
        }))

    async def broadcast_status(self, event):
        """
        Handler for 'broadcast_status' group messages.
        Sends a delivery status change (e.g. IN_TRANSIT, DELIVERED) to this connection.
        """
        await self.send(json.dumps({
            "type": "status_update",
            "status": event["status"],
        }))

    async def broadcast_completion(self, event):
        """
        Handler for 'broadcast_completion' group messages.
        Sent when the biker marks the delivery as DELIVERED via the REST API.
        Notifies all connected clients that the delivery is complete.
        """
        await self.send(json.dumps({
            "type": "delivery_completed",
            "message": "Delivery has been completed"
        }))

    async def delivery_request(self, event):
        """
        Handler for 'delivery_request' group messages.
        Sent by the server (via views.py perform_create) to notify a biker
        of a new delivery near their location.
        Forwards the delivery details to the biker's WebSocket connection.
        """
        await self.send(json.dumps({
            "type": "delivery_request",
            "delivery_id": event["delivery_id"],
            "pickup_address": event["pickup_address"],
            "dropoff_address": event["dropoff_address"],
        }))

    # =====================================
    # DATABASE HELPERS (sync -> async)
    # =====================================

    @database_sync_to_async
    def get_delivery(self, delivery_id):
        """Fetch a delivery by ID. Returns None if not found."""
        try:
            return Delivery.objects.get(id=delivery_id)
        except Delivery.DoesNotExist:
            return None

    @database_sync_to_async
    def get_assignment(self, delivery_id):
        """
        Fetch the assignment for a delivery, including the related biker and user.
        Returns None if no assignment exists.
        """
        try:
            return DeliveryAssignment.objects.select_related(
                "biker__user"
            ).get(delivery_id=delivery_id)
        except DeliveryAssignment.DoesNotExist:
            return None

    @database_sync_to_async
    def get_user_role(self, user):
        """
        Determine the role of the connecting user:
        - 'admin' if they are staff
        - 'biker' if they have a linked Biker profile
        - 'client' otherwise
        """
        if user.is_staff:
            return "admin"

        if Biker.objects.filter(user=user).exists():
            return "biker"

        return "client"

    @database_sync_to_async
    def save_location(self, latitude, longitude):
        """Save a biker's location update to the DeliveryLocation table."""
        DeliveryLocation.objects.create(
            delivery=self.delivery,
            biker=self.biker,
            latitude=latitude,
            longitude=longitude,
            recorded_at=timezone.now()
        )

    @database_sync_to_async
    def auto_start_delivery(self):
        """
        Automatically transitions a delivery from ASSIGNED to IN_TRANSIT
        when the biker sends their first location update.
        Also updates the biker's status to ON_DELIVERY and logs the event.
        """
        if self.delivery.status == "ASSIGNED":
            self.delivery.status = "IN_TRANSIT"
            self.delivery.save()

            self.biker.status = "ON_DELIVERY"
            self.biker.save()

            DeliveryLog.objects.create(
                delivery=self.delivery,
                message="Delivery started (IN_TRANSIT)"
            )


# =====================================
# BIKER CONSUMER
# Used by: bikers to receive incoming delivery job notifications
# URL: ws://biker/
# =====================================
class BikerConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for bikers to receive delivery request notifications.
    - Biker connects once when they open the app and stays connected.
    - When a client creates a delivery, nearby bikers receive a delivery_request message here.
    - No delivery_id needed in the URL — the biker just listens on their personal channel.
    """

    async def connect(self):
        """
        Called when a biker opens a WebSocket connection.
        - Rejects anonymous users.
        - Verifies the user has a biker profile.
        - Adds the biker to their personal group: biker_<id>
        - This group is what views.py sends delivery_request messages to.
        """
        user = self.scope["user"]

        # Reject unauthenticated connections
        if not user or user.is_anonymous:
            await self.close(code=4001)
            return

        # Verify the user is actually a biker
        self.biker = await self.get_biker(user)
        if not self.biker:
            await self.close(code=4003)  # Not a biker
            return

        # Personal group name — matches what views.py sends to: f"biker_{biker.id}"
        self.group_name = f"biker_{self.biker.id}"

        # Join the personal biker group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Accept the connection
        await self.accept()

        # Confirm connection to the biker
        await self.send(json.dumps({
            "type": "connection_established",
            "message": "Listening for delivery requests",
            "biker_id": self.biker.id
        }))

    async def disconnect(self, close_code):
        """
        Called when the biker disconnects.
        Removes them from their personal group.
        """
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def delivery_request(self, event):
        """
        Handler for 'delivery_request' group messages.
        Called when views.py sends a new delivery notification to this biker's group.
        Forwards the delivery details to the biker's WebSocket.
        """
        await self.send(json.dumps({
            "type": "delivery_request",
            "delivery_id": event["delivery_id"],
            "pickup_address": event["pickup_address"],
            "dropoff_address": event["dropoff_address"],
        }))

    async def delivery_taken(self, event):
        """
        Handler for 'delivery_taken' group messages.
        Called when another biker has accepted a delivery that was sent to this biker too.
        Notifies the biker so their UI can remove it from their available jobs list.
        """
        await self.send(json.dumps({
            "type": "delivery_taken",
            "delivery_id": event["delivery_id"],
            "message": event["message"]
        }))

    # =====================================
    # DATABASE HELPERS
    # =====================================

    @database_sync_to_async
    def get_biker(self, user):
        """Fetch the biker profile for this user. Returns None if not a biker."""
        try:
            return Biker.objects.get(user=user)
        except Biker.DoesNotExist:
            return None

# Note: delivery_taken handler added below delivery_request in BikerConsumer