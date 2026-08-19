from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .game_state import RoomState
from .models import GameDeck, Room
from .state_store import get_store


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
        self.store = get_store()

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        state = await self.load_state()
        state.connected_user_ids.add(user.id)
        await self.save_and_broadcast(state)

    async def disconnect(self, close_code):
        if not hasattr(self, "room"):
            return
        state = await self.load_state()
        state.connected_user_ids.discard(self.user.id)
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.save_and_broadcast(state)

    async def receive_json(self, content, **kwargs):
        message_type = content.get("type")
        state = await self.load_state()

        if message_type == "ready":
            deck = await self.get_deck(content.get("deck_id"))
            if deck is None:
                await self.send_json({"type": "error", "message": "Deck not found."})
                return
            try:
                state.mark_ready(self.room, self.user.id, deck)
            except PermissionError as exc:
                await self.send_json({"type": "error", "message": str(exc)})
                return
            await self.save_and_broadcast(state)
        elif message_type == "pass_phase":
            try:
                state.pass_phase(self.room, self.user.id)
            except PermissionError as exc:
                await self.send_json({"type": "error", "message": str(exc)})
                return
            await self.save_and_broadcast(state)
        elif message_type == "rematch":
            try:
                state.rematch(self.room, self.user.id)
            except PermissionError as exc:
                await self.send_json({"type": "error", "message": str(exc)})
                return
            await self.save_and_broadcast(state)
        elif message_type == "chat":
            text = str(content.get("text", "")).strip()[:500]
            if text:
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "room.chat", "user_id": self.user.id, "username": self.user.username, "text": text},
                )

    async def load_state(self):
        state = await self.store.get(self.room_code)
        if state is None:
            state = RoomState()
        state.ensure_sides(self.room)
        return state

    async def save_and_broadcast(self, state):
        await self.store.save(self.room_code, state)
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "room.update", "state": state.as_dict(self.room)},
        )

    async def room_update(self, event):
        await self.send_json(event["state"])

    async def room_chat(self, event):
        await self.send_json(
            {"type": "chat", "user_id": event["user_id"], "username": event["username"], "text": event["text"]}
        )

    @sync_to_async
    def get_room(self, code):
        return Room.objects.filter(code=code).select_related("created_by", "player_two").first()

    @sync_to_async
    def get_deck(self, deck_id):
        if not deck_id:
            return None
        return GameDeck.objects.filter(id=deck_id).first()
