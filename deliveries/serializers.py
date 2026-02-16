from rest_framework import serializers
from .models import (
    Delivery,
    DeliveryAssignment,
    DeliveryLocation,
)


class DeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery
        fields = "__all__"
        read_only_fields = ("status", "created_at")


class DeliveryAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAssignment
        fields = "__all__"
        read_only_fields = ("assigned_at",)


class DeliveryLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryLocation
        fields = "__all__"
        read_only_fields = ("recorded_at",)
