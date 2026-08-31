from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/game/(?P<room_code>[A-Z0-9]{6})/$', consumers.RoomConsumer.as_asgi()),
]
