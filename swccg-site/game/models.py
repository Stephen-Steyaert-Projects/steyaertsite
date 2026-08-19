import random
import string
import uuid

from django.conf import settings
from django.db import models

from swccgdb.models import Card

CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_LENGTH = 6


def generate_room_code():
    while True:
        code = ''.join(random.choices(CODE_ALPHABET, k=CODE_LENGTH))
        if not Room.objects.filter(code=code).exists():
            return code


class GameDeck(models.Model):
    """
    A deck built for the online game, from the full card pool (not gated by physical
    ownership — see handoff doc's deliberate MVP ownership decision). Deliberately
    separate from swccgdb.Deck, which represents the user's physical-collection decks
    on the main site.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='game_decks')
    name = models.CharField(max_length=200)
    side = models.CharField(max_length=1, choices=Card.Side.choices)
    cards = models.ManyToManyField(Card, through='GameDeckCard', related_name='game_decks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def card_count(self):
        return self.deck_cards.aggregate(total=models.Sum('quantity'))['total'] or 0

    @property
    def is_valid(self):
        return self.card_count == 60

    def __str__(self):
        return f"{self.name} ({self.user})"


class GameDeckCard(models.Model):
    game_deck = models.ForeignKey(GameDeck, on_delete=models.CASCADE, related_name='deck_cards')
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='game_deck_cards')
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = ('game_deck', 'card')

    def __str__(self):
        return f"{self.game_deck} — {self.card} x{self.quantity}"


class Room(models.Model):
    """
    A shareable match lobby. Deliberately does NOT pin either player to a specific deck —
    side is randomized per game (and swaps on a rematch) and each player picks which of
    their decks to bring on a "ready" screen before each game starts. See game_state.py
    for that ephemeral, per-game state.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=CODE_LENGTH, unique=True, default=generate_room_code)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rooms_created')
    player_two = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rooms_joined', null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    @property
    def is_full(self):
        return self.player_two_id is not None

    def has_player(self, user):
        return user.is_authenticated and user.id in (self.created_by_id, self.player_two_id)

    def role_for_user_id(self, user_id):
        if user_id == self.created_by_id:
            return 'creator'
        if user_id == self.player_two_id:
            return 'player_two'
        return None

    def user_id_for_role(self, role):
        return self.created_by_id if role == 'creator' else self.player_two_id

    def promote_player_two_to_creator(self):
        """Used when the creator is kicked for idling: player_two becomes creator, freeing the player_two slot."""
        Room.objects.filter(pk=self.pk).update(created_by_id=self.player_two_id, player_two_id=None)

    def clear_player_two(self):
        Room.objects.filter(pk=self.pk).update(player_two_id=None)

    def remove_player(self, user_id):
        """
        Frees this user's slot (promoting player_two to creator if they were the
        creator), or deletes the room outright if that would leave it empty.
        Returns True if the room was deleted.
        """
        if user_id == self.created_by_id:
            if self.player_two_id is None:
                self.delete()
                return True
            self.promote_player_two_to_creator()
            return False
        if user_id == self.player_two_id:
            self.clear_player_two()
            return False
        return False
