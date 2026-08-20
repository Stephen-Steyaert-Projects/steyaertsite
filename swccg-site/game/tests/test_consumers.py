from asgiref.sync import sync_to_async
import pytest

from swccgdb.models import Card

from game.factories import RoomFactory, make_full_deck
from game.models import GameDeckCard

pytestmark = pytest.mark.django_db(transaction=True)


async def receive_until(comm, msg_type, predicate=None, max_messages=15, timeout=5):
    """Drains messages from one communicator's queue until it sees one matching msg_type
    (and predicate, if given). Robust against however many other broadcasts are interleaved —
    e.g. every player action broadcasts a 'state' message to both sockets, so exact message
    counts aren't a reliable thing to assert on. Generous per-message timeout: each hop can
    involve several sync_to_async DB round-trips stacking up under test-suite load."""
    for _ in range(max_messages):
        msg = await comm.receive_json_from(timeout=timeout)
        if msg["type"] == msg_type and (predicate is None or predicate(msg)):
            return msg
    raise AssertionError(f"Never received a {msg_type!r} message matching the predicate")


@sync_to_async
def sync_make_full_deck(user, side):
    return make_full_deck(user, side)


@sync_to_async
def get_first_location_id(deck_id):
    return GameDeckCard.objects.filter(
        game_deck_id=deck_id, card__card_type=Card.CardType.LOCATION,
    ).values_list("card_id", flat=True).first()


async def get_to_in_progress(room, creator_comm, p2_comm):
    """Drives both players through ready + starting-location selection until the game
    deals cards. Returns (dark_comm, light_comm, state_after_start) — whichever
    communicator ended up on which side (randomized), plus the game-starting state
    broadcast (cards_dealt=True), already drained from dark_comm's queue."""
    state_msg = await receive_until(creator_comm, "state")
    my_side = state_msg["side_by_user_id"][str(room.created_by_id)]
    dark_comm, dark_user = (creator_comm, room.created_by) if my_side == 'D' else (p2_comm, room.player_two)
    light_comm, light_user = (p2_comm, room.player_two) if my_side == 'D' else (creator_comm, room.created_by)

    dark_deck = await sync_make_full_deck(dark_user, Card.Side.DARK)
    light_deck = await sync_make_full_deck(light_user, Card.Side.LIGHT)

    await dark_comm.send_json_to({"type": "ready", "deck_id": str(dark_deck.id)})
    await receive_until(dark_comm, "location_options")

    dark_location_id = await get_first_location_id(dark_deck.id)
    await dark_comm.send_json_to({"type": "choose_starting_location", "location_card_id": dark_location_id})

    await light_comm.send_json_to({"type": "ready", "deck_id": str(light_deck.id)})
    await receive_until(light_comm, "location_options")

    light_location_id = await get_first_location_id(light_deck.id)
    await light_comm.send_json_to({"type": "choose_starting_location", "location_card_id": light_location_id})

    # This is the game-starting action: both sockets get a 'state' broadcast with
    # cards_dealt=True, plus their own private 'your_hand' message.
    state_after_start = await receive_until(dark_comm, "state", predicate=lambda m: m.get("cards_dealt"))
    await receive_until(light_comm, "state", predicate=lambda m: m.get("cards_dealt"))

    return dark_comm, light_comm, state_after_start


@pytest.fixture
def two_player_room():
    return RoomFactory()


class TestGameStartsAndDealsCards:
    async def test_both_players_receive_their_own_private_hand(self, two_player_room, comms):
        room = two_player_room
        creator_comm = await comms(room, room.created_by)
        p2_comm = await comms(room, room.player_two)

        dark_comm, light_comm, _ = await get_to_in_progress(room, creator_comm, p2_comm)

        dark_hand_msg = await receive_until(dark_comm, "your_hand")
        light_hand_msg = await receive_until(light_comm, "your_hand")
        assert len(dark_hand_msg["cards"]) == 8
        assert len(light_hand_msg["cards"]) == 8

    async def test_hand_cards_include_names(self, two_player_room, comms):
        room = two_player_room
        creator_comm = await comms(room, room.created_by)
        p2_comm = await comms(room, room.player_two)

        dark_comm, light_comm, _ = await get_to_in_progress(room, creator_comm, p2_comm)
        dark_hand_msg = await receive_until(dark_comm, "your_hand")

        assert all(c["name"] for c in dark_hand_msg["cards"])

    async def test_state_broadcast_exposes_pile_sizes_not_hand_contents(self, two_player_room, comms):
        room = two_player_room
        creator_comm = await comms(room, room.created_by)
        p2_comm = await comms(room, room.player_two)

        dark_comm, light_comm, state_msg = await get_to_in_progress(room, creator_comm, p2_comm)

        assert "hand" not in state_msg
        sizes = list(state_msg["pile_sizes_by_user_id"].values())
        assert len(sizes) == 2
        assert all(s["hand"] == 8 and s["reserve_deck"] == 51 for s in sizes)


class TestActivateForceAndDrawOverWebsocket:
    async def test_activate_moves_reserve_to_force_pile(self, two_player_room, comms):
        room = two_player_room
        creator_comm = await comms(room, room.created_by)
        p2_comm = await comms(room, room.player_two)

        dark_comm, light_comm, _ = await get_to_in_progress(room, creator_comm, p2_comm)

        await dark_comm.send_json_to({"type": "activate_force", "count": 1})
        state_msg = await receive_until(
            dark_comm, "state", predicate=lambda m: m["pile_sizes_by_user_id"][str(m["active_user_id"])]["force_pile"] == 1,
        )
        my_sizes = state_msg["pile_sizes_by_user_id"][str(state_msg["active_user_id"])]
        assert my_sizes["force_pile"] == 1
        assert my_sizes["reserve_deck"] == 50

    async def test_activate_force_rejected_off_turn(self, two_player_room, comms):
        room = two_player_room
        creator_comm = await comms(room, room.created_by)
        p2_comm = await comms(room, room.player_two)

        dark_comm, light_comm, _ = await get_to_in_progress(room, creator_comm, p2_comm)

        await light_comm.send_json_to({"type": "activate_force", "count": 1})
        error_msg = await receive_until(light_comm, "error")
        assert "your turn" in error_msg["message"]
