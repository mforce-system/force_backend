from django.urls import re_path
from .consumers import TrackingConsumer

websocket_urlpatterns = [
    re_path(r"ws/tracking/(?P<delivery_id>\d+)/$", TrackingConsumer.as_asgi()),
]
