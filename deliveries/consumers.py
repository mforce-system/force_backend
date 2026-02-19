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


class TrackingConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope["user"]

        if not user or user.is_anonymous:
            await self.close(code=4001)
            return

        self.delivery_id = self.scope["url_route"]["kwargs"]["delivery_id"]
        self.group_name = f"delivery_{self.delivery_id}"

        self.delivery = await self.get_delivery(self.delivery_id)
        if not self.delivery:
            await self.close(code=4004)
            return

        # SAFE ROLE DETECTION
        self.role = await self.get_user_role(user)

        if self.role == "biker":
            assignment = await self.get_assignment(self.delivery_id)

            if not assignment or not assignment.accepted:
                await self.close(code=4003)
                return

            if assignment.biker.user.id != user.id:
                await self.close(code=4003)
                return

            self.biker = assignment.biker

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        await self.send(json.dumps({
            "type": "connection_established",
            "delivery_id": self.delivery_id,
            "role": self.role
        }))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)

        if self.role == "biker" and data.get("type") == "location_update":
            latitude = data.get("latitude")
            longitude = data.get("longitude")

            await self.save_location(latitude, longitude)
            await self.auto_start_delivery()

            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "broadcast_location",
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )

    async def broadcast_location(self, event):
        await self.send(json.dumps({
            "type": "location_update",
            "latitude": event["latitude"],
            "longitude": event["longitude"],
        }))

    async def broadcast_status(self, event):
        await self.send(json.dumps({
            "type": "status_update",
            "status": event["status"],
        }))

    @database_sync_to_async
    def get_delivery(self, delivery_id):
        try:
            return Delivery.objects.get(id=delivery_id)
        except Delivery.DoesNotExist:
            return None

    @database_sync_to_async
    def get_assignment(self, delivery_id):
        try:
            return DeliveryAssignment.objects.select_related(
                "biker__user"
            ).get(delivery_id=delivery_id)
        except DeliveryAssignment.DoesNotExist:
            return None

    @database_sync_to_async
    def get_user_role(self, user):
        if user.is_staff:
            return "admin"

        if Biker.objects.filter(user=user).exists():
            return "biker"

        return "client"

    @database_sync_to_async
    def save_location(self, latitude, longitude):
        DeliveryLocation.objects.create(
            delivery=self.delivery,
            biker=self.biker,
            latitude=latitude,
            longitude=longitude,
            recorded_at=timezone.now()
        )

    @database_sync_to_async
    def auto_start_delivery(self):
        if self.delivery.status == "ASSIGNED":
            self.delivery.status = "IN_TRANSIT"
            self.delivery.save()

            self.biker.status = "ON_DELIVERY"
            self.biker.save()

            DeliveryLog.objects.create(
                delivery=self.delivery,
                message="Delivery started (IN_TRANSIT)"
            )
