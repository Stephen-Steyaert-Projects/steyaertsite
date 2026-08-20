import pytest

from swccgdb.models import Card

from game.factories import RoomFactory
from game.game_state import PHASE_ORDER, Phase, RoomState

pytestmark = pytest.mark.django_db


def make_ready_state(room):
    """A RoomState with both players fully readied up but cards not yet dealt."""
    state = RoomState()
    state.side_by_role = {'creator': Card.Side.DARK, 'player_two': Card.Side.LIGHT}
    state.ready_decks = {'creator': 'deck-1', 'player_two': 'deck-2'}
    state.starting_locations = {'creator': 100, 'player_two': 200}
    state._maybe_start_game()
    return state


def deal(state, creator_extra=None, player_two_extra=None):
    creator_cards = [100] + list(range(1, 60))
    player_two_cards = [200] + list(range(1000, 1059))
    role_cards = {
        'creator': creator_extra if creator_extra is not None else creator_cards,
        'player_two': player_two_extra if player_two_extra is not None else player_two_cards,
    }
    state.deal_cards(role_cards, {'creator': 2, 'player_two': 3})
    return state


class TestDealCards:
    def test_deals_8_to_hand_and_51_to_reserve(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        assert len(state.hand['creator']) == 8
        assert len(state.reserve_deck['creator']) == 51
        assert len(state.hand['player_two']) == 8
        assert len(state.reserve_deck['player_two']) == 51

    def test_starting_location_is_removed_from_the_deck(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        all_creator_cards = state.hand['creator'] + state.reserve_deck['creator']
        assert 100 not in all_creator_cards
        assert len(all_creator_cards) == 59

    def test_other_piles_start_empty(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        assert state.force_pile == {'creator': [], 'player_two': []}
        assert state.used_pile == {'creator': [], 'player_two': []}
        assert state.lost_pile == {'creator': [], 'player_two': []}
        assert state.cards_dealt is True

    def test_caches_max_force_from_starting_location_icons(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        assert state.max_force == {'creator': 2, 'player_two': 3}

    def test_preserves_duplicate_card_ids_from_deck_quantities(self):
        """A deck can legally run multiple copies of the same card (same card id, qty > 1)."""
        room = RoomFactory()
        creator_cards = [100] + [5] * 3 + list(range(6, 62))  # 60 total, card 5 x3, rest unique
        state = deal(make_ready_state(room), creator_extra=creator_cards)
        all_creator_cards = state.hand['creator'] + state.reserve_deck['creator']
        assert all_creator_cards.count(5) == 3
        assert len(all_creator_cards) == 59


class TestActivateForce:
    def test_moves_cards_from_reserve_to_force_pile(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        state.activate_force(room, room.created_by_id, 2)
        assert len(state.force_pile['creator']) == 2
        assert len(state.reserve_deck['creator']) == 49

    def test_rejects_more_than_max_force_plus_one(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        with pytest.raises(PermissionError):
            state.activate_force(room, room.created_by_id, 4)  # max_force=2, allowed 0..3

    def test_allows_exactly_max_force_plus_one(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        state.activate_force(room, room.created_by_id, 3)
        assert len(state.force_pile['creator']) == 3

    def test_rejects_when_not_your_turn(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        with pytest.raises(PermissionError):
            state.activate_force(room, room.player_two_id, 1)

    def test_rejects_outside_activate_phase(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        state.phase_index = PHASE_ORDER.index(Phase.CONTROL)
        with pytest.raises(PermissionError):
            state.activate_force(room, room.created_by_id, 1)

    def test_rejects_more_than_reserve_deck_size(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        state.max_force['creator'] = 100
        with pytest.raises(PermissionError):
            state.activate_force(room, room.created_by_id, 60)


class TestDrawCards:
    def test_moves_cards_from_force_pile_to_hand(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        state.activate_force(room, room.created_by_id, 2)
        state.phase_index = PHASE_ORDER.index(Phase.DRAW)
        state.draw_cards(room, room.created_by_id, 2)
        assert len(state.hand['creator']) == 10
        assert len(state.force_pile['creator']) == 0

    def test_rejects_more_than_force_pile_size(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        state.phase_index = PHASE_ORDER.index(Phase.DRAW)
        with pytest.raises(PermissionError):
            state.draw_cards(room, room.created_by_id, 1)

    def test_rejects_outside_draw_phase(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        with pytest.raises(PermissionError):
            state.draw_cards(room, room.created_by_id, 0)


class TestPassPhaseAndEndTurn:
    def test_pass_phase_advances_through_activate_to_draw(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        for _ in range(len(PHASE_ORDER) - 1):
            state.pass_phase(room, room.created_by_id)
        assert PHASE_ORDER[state.phase_index] == Phase.DRAW

    def test_pass_phase_no_longer_wraps_the_turn(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        for _ in range(len(PHASE_ORDER) - 1):
            state.pass_phase(room, room.created_by_id)
        with pytest.raises(PermissionError):
            state.pass_phase(room, room.created_by_id)
        assert state.turn_number == 1
        assert state.active_side == Card.Side.DARK

    def test_end_turn_recirculates_used_pile_beneath_reserve_preserving_order(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        state.used_pile['creator'] = [11, 22, 33]
        state.reserve_deck['creator'] = [1, 2, 3]
        state.phase_index = PHASE_ORDER.index(Phase.DRAW)
        state.end_turn(room, room.created_by_id)
        assert state.reserve_deck['creator'] == [11, 22, 33, 1, 2, 3]
        assert state.used_pile['creator'] == []

    def test_end_turn_flips_active_side_and_resets_phase(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        state.phase_index = PHASE_ORDER.index(Phase.DRAW)
        state.end_turn(room, room.created_by_id)
        assert state.active_side == Card.Side.LIGHT
        assert state.phase_index == 0
        assert state.turn_number == 2

    def test_end_turn_rejects_outside_draw_phase(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        with pytest.raises(PermissionError):
            state.end_turn(room, room.created_by_id)

    def test_end_turn_rejects_when_not_your_turn(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        state.phase_index = PHASE_ORDER.index(Phase.DRAW)
        with pytest.raises(PermissionError):
            state.end_turn(room, room.player_two_id)


class TestLifeForceDepletion:
    def test_no_depletion_right_after_deal(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        assert state.check_life_force_depletion() is None

    def test_depletion_when_reserve_and_force_and_used_all_empty(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        state.reserve_deck['creator'] = []
        state.force_pile['creator'] = []
        state.used_pile['creator'] = []
        assert state.check_life_force_depletion() == 'creator'
        assert state.ended_by_role == 'creator'
        assert state.status == 'game_over'

    def test_no_depletion_before_cards_are_dealt(self):
        room = RoomFactory()
        state = make_ready_state(room)
        assert state.check_life_force_depletion() is None


class TestRematchResetsPiles:
    def test_rematch_clears_piles_and_deal_flag(self):
        room = RoomFactory()
        state = deal(make_ready_state(room))
        state.phase_index = PHASE_ORDER.index(Phase.DRAW)
        state.end_turn(room, room.created_by_id)
        state.ended_by_role = 'player_two'  # simulate game over
        state.rematch(room, room.created_by_id)
        assert state.cards_dealt is False
        assert state.hand == {}
        assert state.reserve_deck == {}
        assert state.max_force == {}
