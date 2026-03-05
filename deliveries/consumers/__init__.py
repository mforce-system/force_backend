# This file makes the consumers directory a Python package
# and exposes both consumers for easy importing in routing.py

from .tracking_consumer import TrackingConsumer
from .biker_consumer import BikerConsumer

__all__ = ["TrackingConsumer", "BikerConsumer"]