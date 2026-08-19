from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .game_state import get_or_create_state
from .models import Room


class RoomConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
        self.group_name = f"room_{self.room_code}"
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close()
            return

        room = await self.get_room(self.room_code)
        if room is None or not room.has_player(user):
            await self.close()
            return

        self.room = room
        self.user = user

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        state = get_or_create_state(room)
        state.connected_user_ids.add(user.id)
        await self.broadcast_state(state)

    async def disconnect(self, close_code):
        if not hasattr(self, "room"):
            return
        state = get_or_create_state(self.room)
        state.connected_user_ids.discard(self.user.id)
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.broadcast_state(state)

    async def receive_json(self, content, **kwargs):
        message_type = content.get("type")
        state = get_or_create_state(self.room)

        if message_type == "pass_phase":
            try:
                state.pass_phase(self.user.id)
            except PermissionError as exc:
                await self.send_json({"type": "error", "message": str(exc)})
                return
            await self.broadcast_state(state)
        elif message_type == "chat":
            text = str(content.get("text", "")).strip()[:500]
            if text:
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "room.chat", "user_id": self.user.id, "username": self.user.username, "text": text},
                )

    async def broadcast_state(self, state):
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "room.update", "state": state.as_dict()},
        )

    async def room_update(self, event):
        await self.send_json({"type": "state", **event["state"]})

    async def room_chat(self, event):
        await self.send_json(
            {"type": "chat", "user_id": event["user_id"], "username": event["username"], "text": event["text"]}
        )

    @sync_to_async
    def get_room(self, code):
        return Room.objects.filter(code=code).select_related("created_by", "player_two").first()
