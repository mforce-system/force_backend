from django.urls import re_path
from .consumers import TrackingConsumer, BikerConsumer

websocket_urlpatterns = [
    # Client/admin tracks a specific delivery in real time
    # Usage: ws://127.0.0.1:8000/ws/tracking/1/?token=xxx
    re_path(r"^ws/tracking/(?P<delivery_id>\d+)/$", TrackingConsumer.as_asgi()),

    # Biker listens for incoming delivery job notifications
    # Usage: ws://127.0.0.1:8000/ws/biker/?token=xxx
    re_path(r"^ws/biker/$", BikerConsumer.as_asgi()),
]