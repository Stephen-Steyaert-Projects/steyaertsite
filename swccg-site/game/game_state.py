"""
Live match state, per room. Deliberately NOT persisted to the database — this is
ephemeral, tied to a single active game (see handoff doc's "Data layer split").
Storage backend (Redis in prod, in-memory in dev) lives in state_store.py.
"""
import json
import random
import time
from dataclasses import dataclass, field
from enum import Enum

from swccgdb.models import Card

ROLES = ('creator', 'player_two')
IDLE_TIMEOUT_SECONDS = 5 * 60


def other_role(role):
    return 'player_two' if role == 'creator' else 'creator'


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
    ready_decks: dict = field(default_factory=dict)        # role -> GameDeck id, chosen fresh each game
    starting_locations: dict = field(default_factory=dict)  # role -> Card id, chosen fresh each game
    phase_index: int = 0
    active_side: str = None
    turn_number: int = 1
    connected_channels: dict = field(default_factory=dict)  # user_id (int) -> channel_name, for targeted kicks
    ended_by_role: str = None            # role who resigned/idled out, once the game is over
    last_action_at: float = None         # unix time of the active player's last real action, during in_progress
    awaiting_ready_since: float = None   # unix time this game started waiting on ready-checks

    @property
    def status(self):
        if self.ended_by_role:
            return 'game_over'
        if not self.side_by_role:
            return 'waiting_for_player'
        if not self._both_fully_ready():
            return 'awaiting_ready'
        return 'in_progress'

    def _both_fully_ready(self):
        return all(r in self.ready_decks and r in self.starting_locations for r in ROLES)

    def ensure_sides(self, room):
        """Randomly assigns Dark/Light once both players are in the room, for the current game."""
        if self.side_by_role or not room.is_full:
            return
        sides = [Card.Side.DARK, Card.Side.LIGHT]
        random.shuffle(sides)
        self.side_by_role = dict(zip(ROLES, sides))
        self.awaiting_ready_since = time.time()

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
            raise PermissionError("That deck isn't complete (needs exactly 60 cards, including at least 1 Location).")

        self.ready_decks[role] = deck.id
        self._maybe_start_game()

    def choose_starting_location(self, room, user_id, card):
        role = room.role_for_user_id(user_id)
        if role is None:
            raise PermissionError("You're not a player in this room.")
        if role not in self.ready_decks:
            raise PermissionError("Pick your deck first.")
        if card.card_type != Card.CardType.LOCATION:
            raise PermissionError("That's not a Location card.")
        if card.side != self.side_by_role[role]:
            raise PermissionError("That location isn't on your side.")

        self.starting_locations[role] = card.id
        self._maybe_start_game()

    def _maybe_start_game(self):
        if self._both_fully_ready():
            self.phase_index = 0
            self.active_side = Card.Side.DARK
            self.turn_number = 1
            self.last_action_at = time.time()

    def active_user_id(self, room):
        if self.status != 'in_progress':
            return None
        role = next((r for r, side in self.side_by_role.items() if side == self.active_side), None)
        return room.user_id_for_role(role) if role else None

    def pass_phase(self, room, user_id):
        if self.status == 'game_over':
            raise PermissionError("This game is over.")
        if self.status != 'in_progress':
            raise PermissionError("The game hasn't started yet.")
        if user_id != self.active_user_id(room):
            raise PermissionError("It's not your turn.")
        self.phase_index += 1
        if self.phase_index >= len(PHASE_ORDER):
            self.phase_index = 0
            self.active_side = Card.Side.LIGHT if self.active_side == Card.Side.DARK else Card.Side.DARK
            self.turn_number += 1
        self.last_action_at = time.time()

    def resign(self, room, user_id):
        role = room.role_for_user_id(user_id)
        if role is None:
            raise PermissionError("You're not a player in this room.")
        if self.status != 'in_progress':
            raise PermissionError("There's no game in progress to resign from.")
        self.ended_by_role = role

    def check_timeout(self):
        """
        Resolves two kinds of stall: an active player gone quiet mid-game (ends the game
        in their opponent's favor), or one player stuck waiting on a ready-check the other
        never completes (bounces the room back to waiting for a replacement). Returns the
        role that timed out, for the caller to kick their socket and free their room slot —
        or None if nothing timed out.
        """
        if self.status == 'in_progress':
            if self.last_action_at is None or time.time() - self.last_action_at < IDLE_TIMEOUT_SECONDS:
                return None
            idle_role = next((r for r, side in self.side_by_role.items() if side == self.active_side), None)
            if idle_role is None:
                return None
            self.ended_by_role = idle_role
            return idle_role

        if self.status == 'awaiting_ready':
            if self.awaiting_ready_since is None or time.time() - self.awaiting_ready_since < IDLE_TIMEOUT_SECONDS:
                return None
            # Only act when it's unambiguous: exactly one side is actually waiting on the other.
            fully_ready_roles = [r for r in ROLES if r in self.ready_decks and r in self.starting_locations]
            if len(fully_ready_roles) != 1:
                return None
            idle_role = next(r for r in ROLES if r not in fully_ready_roles)
            self.side_by_role = {}
            self.ready_decks = {}
            self.starting_locations = {}
            self.awaiting_ready_since = None
            return idle_role

        return None

    def rematch(self, room, user_id):
        if room.role_for_user_id(user_id) is None:
            raise PermissionError("You're not a player in this room.")
        if self.status != 'game_over':
            raise PermissionError("Finish this game (or resign) before starting a new one.")
        if not room.is_full:
            raise PermissionError("Waiting for a second player to join before you can play again.")
        self.game_number += 1
        self.side_by_role = {role: side for role, side in zip(ROLES, reversed(list(self.side_by_role.values())))}
        self.ready_decks = {}
        self.starting_locations = {}
        self.ended_by_role = None
        self.phase_index = 0
        self.active_side = None
        self.turn_number = 1
        self.last_action_at = None
        self.awaiting_ready_since = time.time()

    def as_dict(self, room):
        resigned_user_id = None
        winner_user_id = None
        if self.status == 'game_over':
            resigned_user_id = room.user_id_for_role(self.ended_by_role)
            winner_user_id = room.user_id_for_role(other_role(self.ended_by_role))

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
            "location_chosen_user_ids": [room.user_id_for_role(role) for role in self.starting_locations],
            "connected_user_ids": sorted(self.connected_channels.keys()),
            "resigned_user_id": resigned_user_id,
            "winner_user_id": winner_user_id,
            "room_is_full": room.is_full,
            "creator_user_id": room.created_by_id,
        }

    def to_json(self):
        return json.dumps({
            "game_number": self.game_number,
            "side_by_role": self.side_by_role,
            "ready_decks": {role: str(deck_id) for role, deck_id in self.ready_decks.items()},
            "starting_locations": self.starting_locations,
            "phase_index": self.phase_index,
            "active_side": self.active_side,
            "turn_number": self.turn_number,
            "connected_channels": self.connected_channels,
            "ended_by_role": self.ended_by_role,
            "last_action_at": self.last_action_at,
            "awaiting_ready_since": self.awaiting_ready_since,
        })

    @classmethod
    def from_json(cls, raw):
        data = json.loads(raw)
        return cls(
            game_number=data["game_number"],
            side_by_role=data["side_by_role"],
            ready_decks=data["ready_decks"],
            starting_locations=data.get("starting_locations", {}),
            phase_index=data["phase_index"],
            active_side=data["active_side"],
            turn_number=data["turn_number"],
            connected_channels={int(uid): ch for uid, ch in data["connected_channels"].items()},
            ended_by_role=data.get("ended_by_role"),
            last_action_at=data.get("last_action_at"),
            awaiting_ready_since=data.get("awaiting_ready_since"),
        )
