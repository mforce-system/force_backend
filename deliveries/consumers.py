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

        self.user = user
        self.delivery_id = self.scope["url_route"]["kwargs"]["delivery_id"]
        self.group_name = f"delivery_{self.delivery_id}"

        self.delivery = await self.get_delivery(self.delivery_id)

        if not self.delivery:
            await self.close(code=4004)
            return

        if user.is_staff:
            self.role = "admin"
        else:
            assignment = await self.get_assignment(self.delivery_id)

            if not assignment or not assignment.accepted:
                await self.close(code=4003)
                return

            if assignment.biker.user.id != user.id:
                await self.close(code=4003)
                return

            self.role = "biker"
            self.biker = assignment.biker

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        await self.send(text_data=json.dumps({
            "message": f"Connected to delivery {self.delivery_id} as {self.role}",
            "delivery_id": self.delivery_id,
            "user_id": user.id,
            "role": self.role
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        if self.role == "biker" and data.get("type") == "location_update":

            latitude = data.get("latitude")
            longitude = data.get("longitude")

            if latitude is None or longitude is None:
                return

            await self.save_location(latitude, longitude)
            await self.start_delivery_if_needed()

            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "send_delivery_location",
                    "biker_id": self.user.id,
                    "delivery_id": self.delivery_id,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )

    async def send_delivery_location(self, event):
        await self.send(text_data=json.dumps({
            "type": "biker_location",
            "delivery_id": event["delivery_id"],
            "biker_id": event["biker_id"],
            "latitude": event["latitude"],
            "longitude": event["longitude"],
        }))

    # ======================
    # DATABASE OPERATIONS
    # ======================

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
    def save_location(self, latitude, longitude):
        DeliveryLocation.objects.create(
            delivery=self.delivery,
            biker=self.biker,
            latitude=latitude,
            longitude=longitude,
            recorded_at=timezone.now()
        )

    @database_sync_to_async
    def start_delivery_if_needed(self):
        if self.delivery.status == "ASSIGNED":
            self.delivery.status = "IN_TRANSIT"
            self.delivery.save()

            self.biker.status = "ON_DELIVERY"
            self.biker.save()

            DeliveryLog.objects.create(
                delivery=self.delivery,
                message="Delivery started (IN_TRANSIT)"
            )
