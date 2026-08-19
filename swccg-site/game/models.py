import random
import string
import uuid

from django.conf import settings
from django.db import models

CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_LENGTH = 6


def generate_room_code():
    while True:
        code = ''.join(random.choices(CODE_ALPHABET, k=CODE_LENGTH))
        if not Room.objects.filter(code=code).exists():
            return code


class Room(models.Model):
    """A shareable match lobby. Live turn/phase state is NOT stored here — see game_state.py."""

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
