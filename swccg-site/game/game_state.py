"""
In-memory live match state, per room. Deliberately NOT persisted to the database —
this is ephemeral, tied to a single active game (see handoff doc's "Data layer split").

Lives in process memory, so this only works correctly with a single ASGI process.
If prod ever scales to multiple worker processes, swap this for a Redis-backed store.
"""
from dataclasses import dataclass, field
from enum import Enum


class Phase(str, Enum):
    ACTIVATE = "Activate"
    CONTROL = "Control"
    DEPLOY = "Deploy"
    BATTLE = "Battle"
    MOVE = "Move"
    DRAW = "Draw"


PHASE_ORDER = [Phase.ACTIVATE, Phase.CONTROL, Phase.DEPLOY, Phase.BATTLE, Phase.MOVE, Phase.DRAW]


@dataclass
class RoomState:
    dark_side_user_id: int
    light_side_user_id: int
    phase_index: int = 0
    active_side: str = "dark"  # Dark Side takes the first turn of the game
    turn_number: int = 1
    connected_user_ids: set = field(default_factory=set)

    @property
    def phase(self):
        return PHASE_ORDER[self.phase_index]

    @property
    def active_user_id(self):
        return self.dark_side_user_id if self.active_side == "dark" else self.light_side_user_id

    def pass_phase(self, user_id):
        if user_id != self.active_user_id:
            raise PermissionError("It's not your turn.")
        self.phase_index += 1
        if self.phase_index >= len(PHASE_ORDER):
            self.phase_index = 0
            self.active_side = "light" if self.active_side == "dark" else "dark"
            self.turn_number += 1

    def as_dict(self):
        return {
            "phase": self.phase.value,
            "turn_number": self.turn_number,
            "active_side": self.active_side,
            "active_user_id": self.active_user_id,
            "dark_side_user_id": self.dark_side_user_id,
            "light_side_user_id": self.light_side_user_id,
            "connected_user_ids": sorted(self.connected_user_ids),
        }


_ROOM_STATES: dict[str, RoomState] = {}


def get_or_create_state(room):
    state = _ROOM_STATES.get(room.code)
    if state is None:
        state = RoomState(
            dark_side_user_id=room.created_by_id,
            light_side_user_id=room.player_two_id,
        )
        _ROOM_STATES[room.code] = state
    return state


def clear_state(room_code):
    _ROOM_STATES.pop(room_code, None)
