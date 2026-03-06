import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from ..models import Biker


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