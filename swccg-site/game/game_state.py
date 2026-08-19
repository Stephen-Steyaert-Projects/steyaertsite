"""
Live match state, per room. Deliberately NOT persisted to the database — this is
ephemeral, tied to a single active game (see handoff doc's "Data layer split").
Storage backend (Redis in prod, in-memory in dev) lives in state_store.py.
"""
import json
import random
from dataclasses import dataclass, field
from enum import Enum

from swccgdb.models import Card

ROLES = ('creator', 'player_two')


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
    game_number: int = 1
    side_by_role: dict = field(default_factory=dict)  # role -> Card.Side value, randomized per game
    ready_decks: dict = field(default_factory=dict)   # role -> GameDeck id, chosen fresh each game
    phase_index: int = 0
    active_side: str = None
    turn_number: int = 1
    connected_user_ids: set = field(default_factory=set)

    @property
    def status(self):
        if not self.side_by_role:
            return 'waiting_for_player'
        if len(self.ready_decks) < 2:
            return 'awaiting_ready'
        return 'in_progress'

    def ensure_sides(self, room):
        """Randomly assigns Dark/Light once both players are in the room, for the current game."""
        if self.side_by_role or not room.is_full:
            return
        sides = [Card.Side.DARK, Card.Side.LIGHT]
        random.shuffle(sides)
        self.side_by_role = dict(zip(ROLES, sides))

    def assigned_side(self, room, user_id):
        role = room.role_for_user_id(user_id)
        return self.side_by_role.get(role)

    def mark_ready(self, room, user_id, deck):
        role = room.role_for_user_id(user_id)
        if role is None:
            raise PermissionError("You're not a player in this room.")
        if not self.side_by_role:
            raise PermissionError("Waiting for both players to join.")
        expected_side = self.side_by_role[role]
        if deck.user_id != user_id:
            raise PermissionError("That's not your deck.")
        if deck.side != expected_side:
            raise PermissionError(f"You were assigned {Card.Side(expected_side).label}. Pick a deck of that side.")
        if not deck.is_valid:
            raise PermissionError("That deck isn't complete (needs exactly 60 cards).")

        self.ready_decks[role] = deck.id
        if len(self.ready_decks) == len(ROLES):
            self.phase_index = 0
            self.active_side = Card.Side.DARK
            self.turn_number = 1

    def active_user_id(self, room):
        if self.status != 'in_progress':
            return None
        role = next((r for r, side in self.side_by_role.items() if side == self.active_side), None)
        return room.user_id_for_role(role) if role else None

    def pass_phase(self, room, user_id):
        if self.status != 'in_progress':
            raise PermissionError("The game hasn't started yet.")
        if user_id != self.active_user_id(room):
            raise PermissionError("It's not your turn.")
        self.phase_index += 1
        if self.phase_index >= len(PHASE_ORDER):
            self.phase_index = 0
            self.active_side = Card.Side.LIGHT if self.active_side == Card.Side.DARK else Card.Side.DARK
            self.turn_number += 1

    def rematch(self, room, user_id):
        if room.role_for_user_id(user_id) is None:
            raise PermissionError("You're not a player in this room.")
        self.game_number += 1
        self.side_by_role = {role: side for role, side in zip(ROLES, reversed(list(self.side_by_role.values())))}
        self.ready_decks = {}
        self.phase_index = 0
        self.active_side = None
        self.turn_number = 1

    def as_dict(self, room):
        return {
            "type": "state",
            "status": self.status,
            "game_number": self.game_number,
            "phase": PHASE_ORDER[self.phase_index].value if self.status == 'in_progress' else None,
            "turn_number": self.turn_number,
            "active_side": self.active_side,
            "active_user_id": self.active_user_id(room),
            "side_by_user_id": {room.user_id_for_role(role): side for role, side in self.side_by_role.items()},
            "ready_user_ids": [room.user_id_for_role(role) for role in self.ready_decks],
            "connected_user_ids": sorted(self.connected_user_ids),
        }

    def to_json(self):
        return json.dumps({
            "game_number": self.game_number,
            "side_by_role": self.side_by_role,
            "ready_decks": {role: str(deck_id) for role, deck_id in self.ready_decks.items()},
            "phase_index": self.phase_index,
            "active_side": self.active_side,
            "turn_number": self.turn_number,
            "connected_user_ids": sorted(self.connected_user_ids),
        })

    @classmethod
    def from_json(cls, raw):
        data = json.loads(raw)
        return cls(
            game_number=data["game_number"],
            side_by_role=data["side_by_role"],
            ready_decks=data["ready_decks"],
            phase_index=data["phase_index"],
            active_side=data["active_side"],
            turn_number=data["turn_number"],
            connected_user_ids=set(data["connected_user_ids"]),
        )
