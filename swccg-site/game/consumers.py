from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from swccgdb.models import Card, CardText

from .game_state import ROLES, RoomState
from .models import GameDeck, GameDeckCard, Room
from .state_store import get_store

FORCE_ICON_STATS_KEY = {Card.Side.DARK: 'darkSideIcons', Card.Side.LIGHT: 'lightSideIcons'}


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

        self.user = user
        self.store = get_store()

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        async with self.store.lock(self.room_code):
            state = await self.load_state(room)

            # If this user already has another tab/connection open on this room, close
            # the old one rather than silently losing track of it.
            stale_channel = state.connected_channels.get(user.id)
            if stale_channel and stale_channel != self.channel_name:
                await self.channel_layer.send(stale_channel, {
                    "type": "kick.close",
                    "reason": "You opened this room in another tab.",
                })

            state.connected_channels[user.id] = self.channel_name
            await self.save_and_broadcast(room, state)
            if state.cards_dealt:
                # A reconnect (e.g. page refresh) otherwise leaves this connection's
                # hand empty until the next action/ping happens to trigger send_hands().
                await self.send_hands(room, state)
            if state.chat_log:
                # Otherwise a reload wipes the visible chat log — it only ever lived in
                # the DOM, never persisted anywhere until now.
                await self.send_json({"type": "chat_history", "messages": state.chat_log})

    async def disconnect(self, close_code):
        if not hasattr(self, "user"):
            return
        room = await self.get_room(self.room_code)
        if room is None:
            return
        async with self.store.lock(self.room_code):
            state = await self.load_state(room)
            # Only clear the slot if it's still us — an idle-kick may have already replaced it.
            if state.connected_channels.get(self.user.id) == self.channel_name:
                del state.connected_channels[self.user.id]
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.save_and_broadcast(room, state)

    async def receive_json(self, content, **kwargs):
        message_type = content.get("type")

        if message_type == "ready":
            deck = await self.get_deck(content.get("deck_id"))
            if deck is None:
                await self.send_json({"type": "error", "message": "Deck not found."})
                return
            deck_is_valid = await self.get_deck_is_valid(deck)
            ok = await self.apply(lambda state, room: state.mark_ready(room, self.user.id, deck, deck_is_valid))
            if ok:
                locations = await self.get_deck_locations(deck.id)
                await self.send_json({"type": "location_options", "locations": locations})
        elif message_type == "choose_starting_location":
            room = await self.get_room(self.room_code)
            state = await self.load_state(room)
            role = room.role_for_user_id(self.user.id)
            deck_id = state.ready_decks.get(role) if role else None
            if not deck_id:
                await self.send_json({"type": "error", "message": "Pick your deck first."})
                return
            card = await self.get_deck_location_card(deck_id, content.get("location_card_id"))
            if card is None:
                await self.send_json({"type": "error", "message": "Invalid location for your deck."})
                return
            await self.apply(lambda state, room: state.choose_starting_location(room, self.user.id, card))
        elif message_type == "pass_phase":
            await self.apply(lambda state, room: state.pass_phase(room, self.user.id))
        elif message_type == "activate_force":
            count = content.get("count")
            await self.apply(lambda state, room: state.activate_force(room, self.user.id, count))
        elif message_type == "draw_cards":
            count = content.get("count")
            await self.apply(lambda state, room: state.draw_cards(room, self.user.id, count))
        elif message_type == "resign":
            await self.apply(lambda state, room: state.resign(room, self.user.id))
        elif message_type == "rematch":
            await self.apply(lambda state, room: state.rematch(room, self.user.id))
        elif message_type == "ping":
            await self.apply(lambda state, room: None)
        elif message_type == "leave":
            await self.leave_room()
        elif message_type == "close_room":
            await self.close_room()
        elif message_type == "chat":
            text = str(content.get("text", "")).strip()[:500]
            if text:
                room = await self.get_room(self.room_code)
                async with self.store.lock(self.room_code):
                    state = await self.load_state(room)
                    state.add_chat_message(self.user.id, self.user.username, text)
                    await self.store.save(self.room_code, state)
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "room.chat", "user_id": self.user.id, "username": self.user.username, "text": text},
                )

    async def apply(self, mutate):
        """Loads fresh state/room, applies a mutation, and broadcasts — or sends back a PermissionError.
        Returns True on success, False if the mutation was rejected."""
        room = await self.get_room(self.room_code)
        async with self.store.lock(self.room_code):
            state = await self.load_state(room)
            try:
                mutate(state, room)
            except PermissionError as exc:
                await self.send_json({"type": "error", "message": str(exc)})
                return False

            if state.status == 'in_progress' and not state.cards_dealt:
                role_cards, role_force_icons = await self.get_role_cards_and_icons(state)
                state.deal_cards(role_cards, role_force_icons)

            state.check_life_force_depletion()

            idle_role = state.check_timeout()
            if idle_role:
                # Mid-game (this idle-out is why the game just ended via resignation)
                # vs. pre-game (still on the ready-check, bounce them and free the slot).
                was_mid_game = state.ended_by_role == idle_role
                reason = (
                    "You were idle too long on your turn and forfeited the game."
                    if was_mid_game
                    else "You took too long to get ready and were removed from the room."
                )
                room = await self.kick_idle_player(room, state, idle_role, reason, reassign_room=not was_mid_game)

            await self.save_and_broadcast(room, state)
            if state.cards_dealt:
                await self.send_hands(room, state)
            return True

    async def send_hands(self, room, state):
        """Hand contents are private — sent individually to each player's own connection(s), never group_send."""
        for role in ROLES:
            user_id = room.user_id_for_role(role)
            channel_name = state.connected_channels.get(user_id)
            if channel_name:
                cards = await self.get_hand_cards(state.hand.get(role, []))
                await self.channel_layer.send(channel_name, {"type": "your.hand", "cards": cards})

    async def your_hand(self, event):
        await self.send_json({"type": "your_hand", "cards": event["cards"]})

    async def kick_idle_player(self, room, state, idle_role, reason, reassign_room):
        """Closes the idle player's socket. reassign_room additionally frees their room
        slot (promoting player_two to creator, or clearing player_two) — only correct
        for the pre-game ready-check bounce, where no game data exists yet. Doing that
        mid-game would reshuffle which DB user holds each role while RoomState's
        per-role fields (side_by_role, hand, piles, ...) keep pointing at the old
        role labels, silently reattaching the survivor to the departed player's side
        and cards instead of their own."""
        kicked_user_id = room.user_id_for_role(idle_role)

        if reassign_room:
            if idle_role == 'creator':
                await self.promote_player_two(room)
            else:
                await self.clear_player_two(room)

        channel_name = state.connected_channels.pop(kicked_user_id, None)
        if channel_name:
            await self.channel_layer.send(channel_name, {"type": "kick.close", "reason": reason})

        return await self.get_room(self.room_code)

    async def leave_room(self):
        """A deliberate exit. Mid-game this counts as resigning; otherwise it just frees your slot."""
        room = await self.get_room(self.room_code)
        if room is None or room.role_for_user_id(self.user.id) is None:
            await self.close()
            return

        async with self.store.lock(self.room_code):
            state = await self.load_state(room)
            if state.status == 'in_progress':
                try:
                    state.resign(room, self.user.id)
                except PermissionError:
                    pass

            state.connected_channels.pop(self.user.id, None)
            deleted = await self.remove_player(room, self.user.id)

            if deleted:
                await self.store.delete(self.room_code)
            else:
                room = await self.get_room(self.room_code)
                await self.save_and_broadcast(room, state)

        await self.close()

    async def close_room(self):
        """Creator-only: tears the room down entirely. Blocked mid-game so it can't be used to deny a loss."""
        room = await self.get_room(self.room_code)
        if room is None:
            return
        if room.created_by_id != self.user.id:
            await self.send_json({"type": "error", "message": "Only the room creator can close the room."})
            return

        async with self.store.lock(self.room_code):
            state = await self.load_state(room)
            if state.status == 'in_progress':
                await self.send_json({"type": "error", "message": "You can't close the room while a game is in progress."})
                return

            other_channel = next(
                (ch for uid, ch in state.connected_channels.items() if uid != self.user.id), None
            )

            await self.destroy_room(room)
            await self.store.delete(self.room_code)

            if other_channel:
                await self.channel_layer.send(other_channel, {
                    "type": "kick.close",
                    "reason": "The room was closed by its creator.",
                })

        await self.close()

    async def kick_close(self, event):
        await self.send_json({"type": "kicked", "message": event.get("reason", "You were disconnected.")})
        await self.close()

    async def load_state(self, room):
        state = await self.store.get(self.room_code)
        if state is None:
            state = RoomState()
        state.ensure_sides(room)
        return state

    async def save_and_broadcast(self, room, state):
        await self.store.save(self.room_code, state)
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "room.update", "state": state.as_dict(room)},
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

    @sync_to_async
    def get_deck_is_valid(self, deck):
        return deck.is_valid

    @sync_to_async
    def get_deck_locations(self, deck_id):
        return list(
            Card.objects.filter(game_deck_cards__game_deck_id=deck_id, card_type=Card.CardType.LOCATION)
            .values("id", "name")
            .order_by("name")
        )

    @sync_to_async
    def get_deck_location_card(self, deck_id, card_id):
        if not card_id:
            return None
        return Card.objects.filter(
            id=card_id, card_type=Card.CardType.LOCATION, game_deck_cards__game_deck_id=deck_id,
        ).first()

    @sync_to_async
    def get_role_cards_and_icons(self, state):
        role_cards = {}
        role_force_icons = {}
        for role in ROLES:
            deck_id = state.ready_decks[role]
            ids = []
            for row in GameDeckCard.objects.filter(game_deck_id=deck_id).values("card_id", "quantity"):
                ids.extend([row["card_id"]] * row["quantity"])
            role_cards[role] = ids

            side = state.side_by_role[role]
            stats_key = FORCE_ICON_STATS_KEY[side]
            location_text = CardText.objects.filter(card_id=state.starting_locations[role]).first()
            role_force_icons[role] = (location_text.stats.get(stats_key, 0) if location_text else 0)
        return role_cards, role_force_icons

    # All the character card_type values collapse to a single "Character" group for hand
    # sorting — a player thinks "characters", not "Rebel" vs "Alien" vs "Sith", etc.
    CHARACTER_CARD_TYPES = {
        Card.CardType.JEDI_MASTER_CHARACTER,
        Card.CardType.REBEL_CHARACTER,
        Card.CardType.REPUBLIC_CHARACTER,
        Card.CardType.ALIEN_CHARACTER,
        Card.CardType.DROID_CHARACTER,
        Card.CardType.DARK_JEDI_MASTER_CHARACTER,
        Card.CardType.IMPERIAL_CHARACTER,
        Card.CardType.SITH_CHARACTER,
    }

    @sync_to_async
    def get_hand_cards(self, card_ids):
        cards_by_id = {
            c["id"]: c for c in Card.objects.filter(id__in=card_ids).values(
                "id", "name", "card_type", "text__image_url", "text__stats",
            )
        }

        def type_group(card_type):
            return "Character" if card_type in self.CHARACTER_CARD_TYPES else Card.CardType(card_type).label

        cards = [
            {
                "id": cid,
                "name": cards_by_id[cid]["name"],
                "image_url": cards_by_id[cid]["text__image_url"] or "",
                # Site cards are scanned rotated 90° from everything else — the compact
                # hand view corrects that; the hover-zoom preview always shows the card
                # as scanned, untouched. Locations also come in "System" (planet) and
                # "Sector" (the Cloud City tier between System and Site) subtypes,
                # neither of which needs correcting — only "Site" specifically does.
                "is_site": (
                    cards_by_id[cid]["card_type"] == Card.CardType.LOCATION
                    and (cards_by_id[cid]["text__stats"] or {}).get("subType") == "Site"
                ),
                "type_group": type_group(cards_by_id[cid]["card_type"]),
            }
            for cid in card_ids if cid in cards_by_id
        ]
        # Group by type (Character, Site, Interrupt, etc.), alphabetically within each group.
        cards.sort(key=lambda c: (c["type_group"], c["name"]))
        return cards

    @sync_to_async
    def promote_player_two(self, room):
        room.promote_player_two_to_creator()

    @sync_to_async
    def clear_player_two(self, room):
        room.clear_player_two()

    @sync_to_async
    def remove_player(self, room, user_id):
        return room.remove_player(user_id)

    @sync_to_async
    def destroy_room(self, room):
        room.delete()
